from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.alerts import check_overdue, escalate_unacknowledged
from app.config import settings
from app.database import get_db
from app.main import app
from app.models import DeliveryLog, utcnow
from app.notifications import sent_messages


def session():
    return next(app.dependency_overrides[get_db]())


def add_confirmed(client, headers, email, name):
    client.post("/buddies", json={"name": name, "email": email}, headers=headers)
    client.post("/buddies/confirm", json={"token": sent_messages[-1]["token"]})


def start_trip(client, headers):
    deadline = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
    return client.post(
        "/trips", json={"label": "Home", "deadline": deadline, "grace_minutes": 1}, headers=headers
    )


def alerted_emails(db):
    rows = db.scalars(select(DeliveryLog).order_by(DeliveryLog.level)).all()
    return [row.buddy_email for row in rows]


def later():
    return utcnow() + (settings.escalation_minutes + 1) * settings.minute


def test_removed_buddy_is_not_alerted(client, auth_headers):
    add_confirmed(client, auth_headers, "old@example.com", "Old")
    add_confirmed(client, auth_headers, "lilly@example.com", "Lilly")
    old_id = client.get("/buddies", headers=auth_headers).json()[0]["id"]
    client.delete(f"/buddies/{old_id}", headers=auth_headers)
    start_trip(client, auth_headers)
    db = session()
    check_overdue(db, now=utcnow() + timedelta(hours=1))
    assert alerted_emails(db) == ["lilly@example.com"]
    db.close()


def test_pending_buddy_is_not_alerted(client, auth_headers):
    client.post("/buddies", json={"name": "Wait", "email": "wait@example.com"}, headers=auth_headers)
    add_confirmed(client, auth_headers, "ok@example.com", "Ok")
    start_trip(client, auth_headers)
    db = session()
    check_overdue(db, now=utcnow() + timedelta(hours=1))
    assert alerted_emails(db) == ["ok@example.com"]
    db.close()


def test_escalates_through_five_buddies_in_order(client, auth_headers):
    emails = [f"b{i}@example.com" for i in range(1, 6)]
    for i, email in enumerate(emails, start=1):
        add_confirmed(client, auth_headers, email, f"B{i}")
    start_trip(client, auth_headers)
    db = session()
    check_overdue(db, now=utcnow() + timedelta(hours=1))
    for _ in range(6):  # more rounds than buddies: it must stop at five
        escalate_unacknowledged(db, now=later())
    assert alerted_emails(db) == emails
    db.close()


def test_acknowledged_alert_stops_escalation(client, auth_headers):
    add_confirmed(client, auth_headers, "a@example.com", "A")
    add_confirmed(client, auth_headers, "b@example.com", "B")
    start_trip(client, auth_headers)
    db = session()
    check_overdue(db, now=utcnow() + timedelta(hours=1))
    first = db.scalar(select(DeliveryLog))
    first.acknowledged_at = utcnow()
    db.commit()
    escalate_unacknowledged(db, now=later())
    assert alerted_emails(db) == ["a@example.com"]
    db.close()