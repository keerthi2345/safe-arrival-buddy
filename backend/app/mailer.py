import smtplib
from email.message import EmailMessage

import httpx

from .config import settings


def email_is_configured() -> bool:
    return bool(settings.brevo_api_key or (settings.smtp_user and settings.smtp_password))


def send_email(to_email: str, subject: str, body: str) -> None:
    """Send one plain-text email. Raises if sending fails."""
    sender = settings.smtp_from or settings.smtp_user

    if settings.brevo_api_key:  # production: HTTPS, so Render's SMTP block doesn't matter
        if not sender:
            raise RuntimeError("SMTP_FROM must be set to your verified Brevo sender address")
        r = httpx.post(
            "https://api.brevo.com/v3/smtp/email",
            headers={"api-key": settings.brevo_api_key, "accept": "application/json"},
            json={
                "sender": {"name": "Safe Arrival Buddy", "email": sender},
                "to": [{"email": to_email}],
                "subject": subject,
                "textContent": body,
            },
            timeout=15,
        )
        r.raise_for_status()
        return

    if settings.smtp_user and settings.smtp_password:  # local: Gmail
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = to_email
        msg.set_content(body)
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
            server.starttls()
            server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
        return

    print(f"\n[DEV EMAIL] To: {to_email}\nSubject: {subject}\n{body}\n")