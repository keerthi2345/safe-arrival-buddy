from .config import settings

# Dev outbox: tests read from this. Phase 6 replaces the print with real SMTP.
sent_messages: list[dict] = []


def send_buddy_confirmation(*, to_email: str, buddy_name: str, traveller_name: str, raw_token: str):
    link = f"{settings.frontend_url}/confirm?token={raw_token}"
    sent_messages.append({"to": to_email, "token": raw_token, "link": link})
    print(
        f"\n[DEV EMAIL] To: {to_email}\n"
        f"Hi {buddy_name}, {traveller_name} wants you as a safe-arrival buddy.\n"
        f"Confirm here: {link}\n"
    )