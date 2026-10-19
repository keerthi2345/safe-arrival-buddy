import smtplib
from email.message import EmailMessage

from .config import settings


def send_email(to: str, subject: str, body: str) -> None:
    if not settings.smtp_host:
        print(f"[DEV EMAIL] To: {to}\nSubject: {subject}\n{body}\n")
        return

    msg = EmailMessage()
    msg["From"] = settings.smtp_from or settings.smtp_user
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
        smtp.starttls()
        if settings.smtp_user:
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(msg)