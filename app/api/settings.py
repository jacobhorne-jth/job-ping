from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr

from app.config import get_settings
from app.services.notifier import EmailNotifier

router = APIRouter(prefix="/settings", tags=["settings"])


class TestEmailRequest(BaseModel):
    recipient_email: EmailStr | None = None


@router.get("")
def settings():
    current = get_settings()
    return {
        "smtp_host": current.smtp_host,
        "smtp_port": current.smtp_port,
        "smtp_username": current.smtp_username,
        "smtp_from_email": current.smtp_from_email,
        "alert_to_email": current.alert_to_email,
        "default_keywords": current.default_keywords,
        "default_exclude_keywords": current.default_exclude_keywords,
        "default_check_interval_minutes": current.default_check_interval_minutes,
        "alert_on_all_jobs": current.alert_on_all_jobs,
        "allow_generic_alerts": current.allow_generic_alerts,
        "max_alerts_per_check": current.max_alerts_per_check,
        "smtp_password_configured": bool(
            current.smtp_password and current.smtp_password != "PASTE_GMAIL_APP_PASSWORD_HERE"
        ),
    }


@router.put("")
def update_settings():
    return {
        "message": "Runtime settings are read from .env for this personal MVP. Edit .env and restart the app."
    }


@router.post("/test-email")
def test_email(payload: TestEmailRequest):
    try:
        EmailNotifier(get_settings()).send_test_email(payload.recipient_email)
        return {"ok": True}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
