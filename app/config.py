from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


DEFAULT_INCLUDE_KEYWORDS = [
    "summer",
    "software engineer intern",
    "software engineering intern",
    "swe intern",
    "backend intern",
    "machine learning intern",
    "data engineering intern",
    "new grad software engineer",
    "university grad",
    "early career",
    "entry level software engineer",
]

DEFAULT_EXCLUDE_KEYWORDS = [
    "senior",
    "staff",
    "principal",
    "manager",
    "director",
    "lead",
    "mechanical",
    "electrical",
    "hardware",
    "sales",
    "marketing",
    "recruiter",
]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:///./direct_job_ping.db"
    app_env: str = "development"
    default_check_interval_minutes: int = 120
    request_timeout_seconds: float = 20.0
    stale_after_missed_checks: int = 3
    alert_on_all_jobs: bool = False
    allow_generic_alerts: bool = False
    max_alerts_per_check: int = 5

    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str | None = None
    alert_to_email: str | None = None

    default_keywords: list[str] = Field(default_factory=lambda: DEFAULT_INCLUDE_KEYWORDS.copy())
    default_exclude_keywords: list[str] = Field(default_factory=lambda: DEFAULT_EXCLUDE_KEYWORDS.copy())


@lru_cache
def get_settings() -> Settings:
    return Settings()
