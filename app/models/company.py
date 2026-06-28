from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    career_url: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False, default="unknown", index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    keywords: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    exclude_keywords: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    locations: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    check_interval_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=120)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    jobs = relationship("Job", back_populates="company", cascade="all, delete-orphan")
    check_runs = relationship("CheckRun", back_populates="company", cascade="all, delete-orphan")
