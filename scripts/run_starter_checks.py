import asyncio

from app.database import SessionLocal
from app.main import STARTER_COMPANY_NAMES
from app.models import Company
from app.services.tracker import check_company


async def main() -> None:
    db = SessionLocal()
    try:
        companies = (
            db.query(Company)
            .filter(Company.name.in_(STARTER_COMPANY_NAMES))
            .order_by(Company.name)
            .all()
        )
        for company in companies:
            result = await check_company(db, company, force=True)
            print(
                company.name,
                result.check_run.status,
                result.jobs_found_count,
                result.new_jobs_count,
                result.matched_jobs_count,
                result.check_run.error_message or "",
                sep="\t",
            )
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
