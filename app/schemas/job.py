from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class NormalizedJob(BaseModel):
    company_name: str
    title: str
    location: str | None = None
    url: str
    external_id: str | None = None
    department: str | None = None
    employment_type: str | None = None
    description: str | None = None
    posted_at: datetime | None = None
    raw_data: dict[str, Any] = {}


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    external_id: str | None
    source_type: str
    title: str
    location: str | None
    department: str | None
    employment_type: str | None
    url: str
    posted_at: datetime | None
    first_seen_at: datetime
    last_seen_at: datetime
    is_active: bool
    matched_keywords: str
