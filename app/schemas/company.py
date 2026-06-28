import json
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CompanyBase(BaseModel):
    name: str
    career_url: str
    source_type: str = "auto"
    enabled: bool = True
    keywords: list[str] = Field(default_factory=list)
    exclude_keywords: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    check_interval_minutes: int = 120
    notes: str | None = None

    @field_validator("keywords", "exclude_keywords", "locations", mode="before")
    @classmethod
    def parse_json_lists(cls, value):
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                return []
            return parsed if isinstance(parsed, list) else []
        return value


class CompanyCreate(CompanyBase):
    pass


class CompanyUpdate(BaseModel):
    name: str | None = None
    career_url: str | None = None
    source_type: str | None = None
    enabled: bool | None = None
    keywords: list[str] | None = None
    exclude_keywords: list[str] | None = None
    locations: list[str] | None = None
    check_interval_minutes: int | None = None
    notes: str | None = None


class CompanyRead(CompanyBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    last_checked_at: datetime | None
    created_at: datetime
    updated_at: datetime
