from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class JobAlert(Base):
    __tablename__ = "job_alerts"
    __table_args__ = (UniqueConstraint("job_id", "alert_type", "recipient_email", name="uq_job_alert_once"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), nullable=False, index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    alert_type: Mapped[str] = mapped_column(String(64), nullable=False, default="email")
    recipient_email: Mapped[str] = mapped_column(String(255), nullable=False)
    matched_keywords: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="sent")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    job = relationship("Job", back_populates="alerts")
