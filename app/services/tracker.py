import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.registry import get_adapter
from app.config import get_settings
from app.models import CheckRun, Company, Job, JobAlert
from app.schemas.job import NormalizedJob
from app.services.json_helpers import dumps_dict, dumps_list, loads_list
from app.services.matcher import match_job
from app.services.notifier import EmailNotifier

TRUSTED_ALERT_SOURCE_TYPES = {
    "amazon_jobs",
    "greenhouse",
    "lever",
    "ashby",
    "google_careers",
    "smartrecruiters",
    "workday",
    "direct_html",
    "phenom_static",
    "oracle_hcm",
    "nextjs_static",
}


@dataclass(frozen=True)
class CheckResult:
    check_run: CheckRun
    jobs_found_count: int
    new_jobs_count: int
    matched_jobs_count: int


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def as_aware_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def stable_fingerprint(company_id: int, source_type: str, job: NormalizedJob) -> str:
    if job.external_id:
        basis = f"external:{company_id}:{source_type}:{job.external_id}"
    elif job.url:
        basis = f"url:{company_id}:{job.url}"
    else:
        basis = f"fallback:{company_id}:{job.title}:{job.location or ''}"
    return hashlib.sha256(basis.lower().encode("utf-8")).hexdigest()


def content_hash(job: NormalizedJob) -> str:
    basis = json.dumps(
        {
            "title": job.title,
            "location": job.location,
            "url": job.url,
            "department": job.department,
            "employment_type": job.employment_type,
            "description": job.description,
        },
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()


def find_existing_job(db: Session, company_id: int, source_type: str, normalized: NormalizedJob) -> Job | None:
    if normalized.external_id:
        return db.scalar(
            select(Job).where(
                Job.company_id == company_id,
                Job.source_type == source_type,
                Job.external_id == normalized.external_id,
            )
        )
    if normalized.url:
        return db.scalar(select(Job).where(Job.company_id == company_id, Job.url == normalized.url))
    fingerprint = stable_fingerprint(company_id, source_type, normalized)
    return db.scalar(select(Job).where(Job.company_id == company_id, Job.fingerprint == fingerprint))


async def check_company(db: Session, company: Company, force: bool = False) -> CheckResult:
    settings = get_settings()
    started_at = now_utc()
    run = CheckRun(company_id=company.id, started_at=started_at, status="running")
    db.add(run)
    db.commit()
    db.refresh(run)

    adapter = get_adapter(company.source_type)
    fetched_fingerprints: set[str] = set()
    new_jobs = 0
    matched_jobs = 0
    alerts_attempted = 0

    try:
        normalized_jobs = await adapter.fetch_jobs(company)
        if settings.alert_on_all_jobs:
            include_keywords = []
            exclude_keywords = []
            locations = []
        else:
            include_keywords = loads_list(company.keywords) or settings.default_keywords
            exclude_keywords = loads_list(company.exclude_keywords) or settings.default_exclude_keywords
            locations = loads_list(company.locations)

        for normalized in normalized_jobs:
            fingerprint = stable_fingerprint(company.id, company.source_type, normalized)
            fetched_fingerprints.add(fingerprint)
            hash_value = content_hash(normalized)
            existing = find_existing_job(db, company.id, company.source_type, normalized)
            match = match_job(normalized, include_keywords, exclude_keywords, locations)

            if existing:
                existing.last_seen_at = started_at
                existing.is_active = True
                existing.missed_check_count = 0
                existing.title = normalized.title
                existing.location = normalized.location
                existing.department = normalized.department
                existing.employment_type = normalized.employment_type
                existing.url = normalized.url
                existing.description = normalized.description
                existing.content_hash = hash_value
                existing.raw_data_json = dumps_dict(normalized.raw_data)
                existing.matched_keywords = dumps_list(match.matched_keywords)
                if match.matched:
                    matched_jobs += 1
                    if _can_send_alert(settings, company) and alerts_attempted < settings.max_alerts_per_check:
                        _record_or_send_alert(db, company, existing)
                        alerts_attempted += 1
                continue

            job = Job(
                company_id=company.id,
                external_id=normalized.external_id,
                source_type=company.source_type,
                title=normalized.title,
                location=normalized.location,
                department=normalized.department,
                employment_type=normalized.employment_type,
                url=normalized.url,
                description=normalized.description,
                posted_at=normalized.posted_at,
                first_seen_at=started_at,
                last_seen_at=started_at,
                is_active=True,
                content_hash=hash_value,
                fingerprint=fingerprint,
                raw_data_json=dumps_dict(normalized.raw_data),
                matched_keywords=dumps_list(match.matched_keywords),
            )
            db.add(job)
            db.flush()
            new_jobs += 1

            if match.matched:
                matched_jobs += 1
                if _can_send_alert(settings, company) and alerts_attempted < settings.max_alerts_per_check:
                    _record_or_send_alert(db, company, job)
                    alerts_attempted += 1

        _mark_missing_jobs(db, company, fetched_fingerprints, settings.stale_after_missed_checks)
        company.last_checked_at = started_at
        run.status = "success"
        run.jobs_found_count = len(normalized_jobs)
        run.new_jobs_count = new_jobs
        run.matched_jobs_count = matched_jobs
        run.finished_at = now_utc()
        db.commit()
        db.refresh(run)
        return CheckResult(run, len(normalized_jobs), new_jobs, matched_jobs)
    except Exception as exc:
        run.status = "failed"
        run.error_message = str(exc)
        run.finished_at = now_utc()
        company.last_checked_at = started_at
        db.commit()
        return CheckResult(run, 0, 0, 0)


def _can_send_alert(settings, company: Company) -> bool:
    return settings.allow_generic_alerts or company.source_type in TRUSTED_ALERT_SOURCE_TYPES


def _record_or_send_alert(db: Session, company: Company, job: Job) -> None:
    settings = get_settings()
    recipient = settings.alert_to_email or "unconfigured@example.com"
    existing = db.scalar(
        select(JobAlert).where(
            JobAlert.job_id == job.id,
            JobAlert.alert_type == "email",
            JobAlert.recipient_email == recipient,
        )
    )
    if existing and existing.status == "sent":
        return

    if existing:
        alert = existing
        alert.matched_keywords = job.matched_keywords
        alert.status = "pending"
        alert.error_message = None
        alert.sent_at = now_utc()
    else:
        alert = JobAlert(
            job_id=job.id,
            company_id=company.id,
            alert_type="email",
            recipient_email=recipient,
            matched_keywords=job.matched_keywords,
            status="pending",
        )
        db.add(alert)
        db.flush()

    try:
        EmailNotifier(settings).send_job_alert(company, job)
        alert.status = "sent"
    except Exception as exc:
        alert.status = "failed"
        alert.error_message = str(exc)


def _mark_missing_jobs(db: Session, company: Company, fetched_fingerprints: set[str], stale_after: int) -> None:
    active_jobs = db.scalars(select(Job).where(Job.company_id == company.id, Job.is_active.is_(True))).all()
    for job in active_jobs:
        if job.fingerprint in fetched_fingerprints:
            continue
        job.missed_check_count += 1
        if job.missed_check_count >= stale_after:
            job.is_active = False


async def run_due_checks(db: Session) -> list[CheckResult]:
    results: list[CheckResult] = []
    current = now_utc()
    companies = db.scalars(select(Company).where(Company.enabled.is_(True))).all()
    for company in companies:
        if company.last_checked_at is None:
            results.append(await check_company(db, company))
            continue
        elapsed = (current - as_aware_utc(company.last_checked_at)).total_seconds() / 60
        if elapsed >= company.check_interval_minutes:
            results.append(await check_company(db, company))
    return results
