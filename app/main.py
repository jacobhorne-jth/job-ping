from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api import checks, companies, jobs, settings
from app.config import get_settings
from app.database import get_db, init_db
from app.models import CheckRun, Company, Job
from app.schemas.company import CompanyCreate, CompanyUpdate
from app.seed import seed_companies
from app.services.company_service import create_company_from_schema, split_form_list, update_company_from_schema
from app.services.json_helpers import loads_list
from app.services.notifier import EmailNotifier
from app.services.scheduler import create_scheduler
from app.services.tracker import check_company

templates = Jinja2Templates(directory="app/templates")
scheduler = create_scheduler()

STARTER_COMPANY_NAMES = {
    "OpenAI",
    "Google",
    "NVIDIA",
    "Stripe",
    "Databricks",
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    db = next(get_db())
    try:
        seed_companies(db)
    finally:
        db.close()
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(title="DirectJobPing", lifespan=lifespan)
app.include_router(companies.router)
app.include_router(jobs.router)
app.include_router(checks.router)
app.include_router(settings.router)


def redirect(path: str) -> RedirectResponse:
    return RedirectResponse(path, status_code=303)


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    total_companies = db.scalar(select(func.count(Company.id))) or 0
    active_jobs = db.scalar(select(func.count(Job.id)).where(Job.is_active.is_(True))) or 0
    new_last_24h = db.scalar(select(func.count(Job.id)).where(Job.first_seen_at >= since)) or 0
    last_check = db.scalar(select(CheckRun).order_by(CheckRun.started_at.desc()).limit(1))
    recent_matched = db.scalars(
        select(Job).where(Job.matched_keywords != "[]").order_by(Job.first_seen_at.desc()).limit(10)
    ).all()
    failures = db.scalars(
        select(CheckRun).where(CheckRun.status == "failed").order_by(CheckRun.started_at.desc()).limit(10)
    ).all()
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "total_companies": total_companies,
            "active_jobs": active_jobs,
            "new_last_24h": new_last_24h,
            "last_check": last_check,
            "recent_matched": recent_matched,
            "failures": failures,
        },
    )


@app.get("/ui/companies", response_class=HTMLResponse)
def companies_page(request: Request, db: Session = Depends(get_db)):
    rows = db.scalars(select(Company).order_by(Company.name)).all()
    return templates.TemplateResponse(
        request,
        "companies.html",
        {"companies": rows, "loads_list": loads_list, "settings": get_settings()},
    )


@app.post("/ui/companies")
def create_company_form(
    name: str = Form(...),
    career_url: str = Form(...),
    source_type: str = Form("auto"),
    keywords: str = Form(""),
    exclude_keywords: str = Form(""),
    locations: str = Form(""),
    check_interval_minutes: int = Form(120),
    enabled: bool = Form(False),
    notes: str = Form(""),
    db: Session = Depends(get_db),
):
    payload = CompanyCreate(
        name=name,
        career_url=career_url,
        source_type=source_type,
        enabled=enabled,
        keywords=split_form_list(keywords),
        exclude_keywords=split_form_list(exclude_keywords),
        locations=split_form_list(locations),
        check_interval_minutes=check_interval_minutes,
        notes=notes,
    )
    db.add(create_company_from_schema(payload))
    db.commit()
    return redirect("/ui/companies")


@app.post("/ui/companies/{company_id}/update")
def update_company_form(
    company_id: int,
    name: str = Form(...),
    career_url: str = Form(...),
    source_type: str = Form("auto"),
    keywords: str = Form(""),
    exclude_keywords: str = Form(""),
    locations: str = Form(""),
    check_interval_minutes: int = Form(120),
    enabled: bool = Form(False),
    notes: str = Form(""),
    db: Session = Depends(get_db),
):
    company = db.get(Company, company_id)
    if company:
        update_company_from_schema(
            company,
            CompanyUpdate(
                name=name,
                career_url=career_url,
                source_type=source_type,
                enabled=enabled,
                keywords=split_form_list(keywords),
                exclude_keywords=split_form_list(exclude_keywords),
                locations=split_form_list(locations),
                check_interval_minutes=check_interval_minutes,
                notes=notes,
            ),
        )
        db.commit()
    return redirect("/ui/companies")


@app.post("/ui/companies/{company_id}/delete")
def delete_company_form(company_id: int, db: Session = Depends(get_db)):
    company = db.get(Company, company_id)
    if company:
        db.delete(company)
        db.commit()
    return redirect("/ui/companies")


@app.post("/ui/companies/{company_id}/check-now")
async def check_company_form(company_id: int, db: Session = Depends(get_db)):
    company = db.get(Company, company_id)
    if company:
        await check_company(db, company, force=True)
    return redirect("/ui/companies")


@app.post("/ui/companies/enable-starter")
def enable_starter_companies(db: Session = Depends(get_db)):
    companies = db.scalars(select(Company).where(Company.name.in_(STARTER_COMPANY_NAMES))).all()
    for company in companies:
        company.enabled = True
    db.commit()
    return redirect("/ui/companies")


@app.post("/ui/companies/disable-all")
def disable_all_companies(db: Session = Depends(get_db)):
    companies = db.scalars(select(Company)).all()
    for company in companies:
        company.enabled = False
    db.commit()
    return redirect("/ui/companies")


@app.post("/ui/companies/check-enabled")
async def check_enabled_companies(db: Session = Depends(get_db)):
    companies = db.scalars(select(Company).where(Company.enabled.is_(True)).order_by(Company.name)).all()
    for company in companies:
        await check_company(db, company, force=True)
    return redirect("/ui/companies")


@app.get("/ui/jobs", response_class=HTMLResponse)
def jobs_page(
    request: Request,
    company_id: int | None = None,
    active: bool | None = None,
    matched: bool | None = None,
    keyword: str | None = None,
    location: str | None = None,
    db: Session = Depends(get_db),
):
    stmt = select(Job).order_by(Job.first_seen_at.desc())
    if company_id:
        stmt = stmt.where(Job.company_id == company_id)
    if active:
        stmt = stmt.where(Job.is_active.is_(True))
    if matched:
        stmt = stmt.where(Job.matched_keywords != "[]")
    if keyword:
        stmt = stmt.where(Job.title.ilike(f"%{keyword}%"))
    if location:
        stmt = stmt.where(Job.location.ilike(f"%{location}%"))
    companies_rows = db.scalars(select(Company).order_by(Company.name)).all()
    return templates.TemplateResponse(
        request,
        "jobs.html",
        {
            "jobs": db.scalars(stmt.limit(500)).all(),
            "companies": companies_rows,
            "loads_list": loads_list,
            "filters": {"company_id": company_id, "active": active, "matched": matched, "keyword": keyword, "location": location},
        },
    )


@app.get("/ui/settings", response_class=HTMLResponse)
def settings_page(request: Request):
    return templates.TemplateResponse(request, "settings.html", {"settings": get_settings(), "message": None})


@app.post("/ui/settings/test-email", response_class=HTMLResponse)
def settings_test_email(request: Request, recipient_email: str = Form("")):
    message = "Test email sent."
    try:
        EmailNotifier(get_settings()).send_test_email(recipient_email or None)
    except Exception as exc:
        message = f"Email failed: {exc}"
    return templates.TemplateResponse(request, "settings.html", {"settings": get_settings(), "message": message})
