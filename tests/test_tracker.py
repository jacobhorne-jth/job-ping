from datetime import datetime, timezone

import pytest

from app.models import Company, JobAlert
from app.schemas.job import NormalizedJob
from app.services.json_helpers import dumps_list
from app.services.tracker import check_company, find_existing_job


class FakeAdapter:
    source_type = "greenhouse"

    def __init__(self, jobs):
        self.jobs = jobs

    async def fetch_jobs(self, company):
        return self.jobs


def make_company(db, source_type="greenhouse"):
    company = Company(
        name="Acme",
        career_url="https://boards.greenhouse.io/acme",
        source_type=source_type,
        enabled=True,
        keywords=dumps_list(["software engineer intern"]),
        exclude_keywords=dumps_list(["senior"]),
        locations=dumps_list([]),
        check_interval_minutes=120,
    )
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


@pytest.mark.asyncio
async def test_deduping_by_external_id_preserves_first_seen(db_session, monkeypatch):
    company = make_company(db_session)
    normalized = NormalizedJob(
        company_name="Acme",
        title="Software Engineer Intern",
        location="Remote",
        url="https://example.com/jobs/1",
        external_id="job-1",
    )
    monkeypatch.setattr("app.services.tracker.get_adapter", lambda source_type: FakeAdapter([normalized]))

    first = await check_company(db_session, company)
    job = find_existing_job(db_session, company.id, company.source_type, normalized)
    first_seen = job.first_seen_at
    second = await check_company(db_session, company)
    db_session.refresh(job)

    assert first.new_jobs_count == 1
    assert second.new_jobs_count == 0
    assert job.first_seen_at == first_seen
    assert job.last_seen_at >= first_seen


@pytest.mark.asyncio
async def test_deduping_by_url(db_session, monkeypatch):
    company = make_company(db_session)
    normalized = NormalizedJob(
        company_name="Acme",
        title="Software Engineer Intern",
        location="Remote",
        url="https://example.com/jobs/url-only",
    )
    monkeypatch.setattr("app.services.tracker.get_adapter", lambda source_type: FakeAdapter([normalized]))

    await check_company(db_session, company)
    result = await check_company(db_session, company)

    assert result.new_jobs_count == 0


@pytest.mark.asyncio
async def test_alert_deduping(db_session, monkeypatch):
    company = make_company(db_session)
    normalized = NormalizedJob(
        company_name="Acme",
        title="Software Engineer Intern",
        location="Remote",
        url="https://example.com/jobs/alert",
        external_id="alert-1",
    )
    monkeypatch.setattr("app.services.tracker.get_adapter", lambda source_type: FakeAdapter([normalized]))

    class NoopNotifier:
        def __init__(self, settings):
            pass

        def send_job_alert(self, company, job):
            return None

    monkeypatch.setattr("app.services.tracker.EmailNotifier", NoopNotifier)
    await check_company(db_session, company)
    await check_company(db_session, company)

    alerts = db_session.query(JobAlert).all()
    assert len(alerts) == 1
    assert alerts[0].status == "sent"
