from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.database import SessionLocal
from app.services.tracker import run_due_checks


async def scheduled_check() -> None:
    db = SessionLocal()
    try:
        await run_due_checks(db)
    finally:
        db.close()


def create_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(scheduled_check, "interval", minutes=5, id="due-company-checks")
    return scheduler
