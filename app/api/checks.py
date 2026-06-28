from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import CheckRun
from app.services.tracker import run_due_checks

router = APIRouter(prefix="/checks", tags=["checks"])


@router.post("/run-all")
async def run_all(db: Session = Depends(get_db)):
    results = await run_due_checks(db)
    return {"checks_run": len(results), "results": [result.check_run.id for result in results]}


@router.get("/recent")
def recent_checks(db: Session = Depends(get_db)):
    return db.scalars(select(CheckRun).order_by(CheckRun.started_at.desc()).limit(50)).all()


@router.get("/{check_id}")
def get_check(check_id: int, db: Session = Depends(get_db)):
    check = db.get(CheckRun, check_id)
    if not check:
        raise HTTPException(status_code=404, detail="Check run not found")
    return check
