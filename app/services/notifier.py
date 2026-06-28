import smtplib
from email.message import EmailMessage

from app.config import Settings
from app.models import Company, Job
from app.services.json_helpers import loads_list


class EmailNotifier:
    def __init__(self, settings: Settings):
        self.settings = settings

    @property
    def configured(self) -> bool:
        return bool(
            self.settings.smtp_host
            and self.settings.smtp_from_email
            and self.settings.alert_to_email
            and self.settings.smtp_password
            and self.settings.smtp_password != "PASTE_GMAIL_APP_PASSWORD_HERE"
        )

    def send_job_alert(self, company: Company, job: Job) -> None:
        if not self.configured:
            raise RuntimeError("SMTP is not configured. Set SMTP_HOST, SMTP_FROM_EMAIL, and ALERT_TO_EMAIL.")

        msg = EmailMessage()
        msg["Subject"] = f"New job: {job.title} at {company.name}"
        msg["From"] = self.settings.smtp_from_email
        msg["To"] = self.settings.alert_to_email
        msg.set_content(
            "\n".join(
                [
                    "New matching job detected",
                    "",
                    f"Company: {company.name}",
                    f"Title: {job.title}",
                    f"Location: {job.location or 'Unknown'}",
                    f"Source: {job.source_type}",
                    f"First seen: {job.first_seen_at}",
                    f"Matched keywords: {', '.join(loads_list(job.matched_keywords))}",
                    "",
                    f"Apply here: {job.url}",
                ]
            )
        )

        with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port, timeout=20) as smtp:
            smtp.starttls()
            if self.settings.smtp_username and self.settings.smtp_password:
                smtp.login(self.settings.smtp_username, self.settings.smtp_password)
            smtp.send_message(msg)

    def send_test_email(self, recipient: str | None = None) -> None:
        if not self.configured:
            raise RuntimeError("SMTP is not configured.")
        msg = EmailMessage()
        msg["Subject"] = "DirectJobPing test email"
        msg["From"] = self.settings.smtp_from_email
        msg["To"] = recipient or self.settings.alert_to_email
        msg.set_content("DirectJobPing SMTP settings are working.")
        with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port, timeout=20) as smtp:
            smtp.starttls()
            if self.settings.smtp_username and self.settings.smtp_password:
                smtp.login(self.settings.smtp_username, self.settings.smtp_password)
            smtp.send_message(msg)
