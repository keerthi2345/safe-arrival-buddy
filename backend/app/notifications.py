from .config import settings
from .mailer import send_email

# Dev outbox: tests read from this.
sent_messages: list[dict] = []


def send_buddy_confirmation(*, to_email: str, buddy_name: str, traveller_name: str, raw_token: str):
    link = f"{settings.frontend_url}/confirm?token={raw_token}"
    sent_messages.append({"to": to_email, "token": raw_token, "link": link})

    subject = f"[Safe Arrival] {traveller_name} wants you as a safe-arrival buddy"
    body = (
        f"Hi {buddy_name},\n\n"
        f"{traveller_name} wants you as a safe-arrival buddy. If you accept, you'll get an email "
        f"only if {traveller_name} doesn't check in on time.\n\n"
        f"Accept here: {link}\n\n"
        f"If you don't know {traveller_name}, ignore this email."
    )
    try:
        send_email(to_email, subject, body)
    except Exception as exc:
        print(f"\n[EMAIL FAILED] To: {to_email} ({exc})\nConfirm link: {link}\n")