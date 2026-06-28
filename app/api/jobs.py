from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Job
from app.schemas.job import JobRead

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=list[JobRead])
def list_jobs(
    company_id: int | None = None,
    active: bool | None = None,
    matched: bool | None = None,
    keyword: str | None = None,
    location: str | None = None,
    first_seen_after: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
):
    stmt = select(Job).order_by(Job.first_seen_at.desc())
    if company_id:
        stmt = stmt.where(Job.company_id == company_id)
    if active is not None:
        stmt = stmt.where(Job.is_active.is_(active))
    if matched:
        stmt = stmt.where(Job.matched_keywords != "[]")
    if keyword:
        stmt = stmt.where(Job.title.ilike(f"%{keyword}%"))
    if location:
        stmt = stmt.where(Job.location.ilike(f"%{location}%"))
    if first_seen_after:
        stmt = stmt.where(Job.first_seen_at >= first_seen_after)
    return db.scalars(stmt.limit(500)).all()


@router.get("/{job_id}", response_model=JobRead)
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
