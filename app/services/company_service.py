from app.config import get_settings
from app.models import Company
from app.schemas.company import CompanyCreate, CompanyUpdate
from app.services.json_helpers import dumps_list
from app.services.source_detector import detect_source_type


def create_company_from_schema(data: CompanyCreate) -> Company:
    settings = get_settings()
    source_type = detect_source_type(data.career_url) if data.source_type in {"auto", "unknown"} else data.source_type
    return Company(
        name=data.name,
        career_url=data.career_url,
        source_type=source_type,
        enabled=data.enabled,
        keywords=dumps_list(data.keywords or settings.default_keywords),
        exclude_keywords=dumps_list(data.exclude_keywords or settings.default_exclude_keywords),
        locations=dumps_list(data.locations),
        check_interval_minutes=data.check_interval_minutes or settings.default_check_interval_minutes,
        notes=data.notes,
    )


def update_company_from_schema(company: Company, data: CompanyUpdate) -> Company:
    update = data.model_dump(exclude_unset=True)
    if "career_url" in update and update["career_url"]:
        company.career_url = update["career_url"]
        if update.get("source_type") in {None, "auto", "unknown"}:
            company.source_type = detect_source_type(company.career_url)
    if "source_type" in update and update["source_type"] and update["source_type"] != "auto":
        company.source_type = update["source_type"]
    for field in ["name", "enabled", "check_interval_minutes", "notes"]:
        if field in update and update[field] is not None:
            setattr(company, field, update[field])
    if "keywords" in update and update["keywords"] is not None:
        company.keywords = dumps_list(update["keywords"])
    if "exclude_keywords" in update and update["exclude_keywords"] is not None:
        company.exclude_keywords = dumps_list(update["exclude_keywords"])
    if "locations" in update and update["locations"] is not None:
        company.locations = dumps_list(update["locations"])
    return company


def split_form_list(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.replace("\n", ",").split(",") if part.strip()]
