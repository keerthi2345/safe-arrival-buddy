from datetime import timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.alerts import check_overdue, retry_failed
from app.config import settings
from app.database import get_db
from app.delivery import send_email
from app.main import app
from app.models import DeliveryLog, Trip, utcnow
from tests.test_trips import make_trip, make_user  # if tests isn't a package, copy these two helpers here


def get_session():
    return next(app.dependency_overrides[get_db]())


def first_trip(db):
    return db.scalar(select(Trip))


def logs(db):
    return db.scalars(select(DeliveryLog)).all()


# Trip deadline is 60 min away with 10 min grace, so the alert fires at +70 min.
def past_grace():
    return utcnow() + timedelta(minutes=71)


@pytest.fixture
def outbox(monkeypatch):
    sent = []
    monkeypatch.setattr(
        "app.alerts.send_email", lambda to, subject, body: sent.append((to, subject, body))
    )
    monkeypatch.setattr(
        "app.alerts.confirmed_buddies",
        lambda db, user_id: [SimpleNamespace(email="mom@example.com")],
    )
    return sent


def test_not_overdue_not_alerted(client, auth_headers, outbox):
    make_trip(client, auth_headers)
    db = get_session()
    assert check_overdue(db) == 0
    assert first_trip(db).status == "active"
    assert outbox == []


def test_within_grace_not_alerted(client, auth_headers, outbox):
    make_trip(client, auth_headers)
    db = get_session()
    assert check_overdue(db, utcnow() + timedelta(minutes=65)) == 0
    assert outbox == []


def test_alerted_after_grace(client, auth_headers, outbox):
    make_trip(client, auth_headers)
    db = get_session()
    assert check_overdue(db, past_grace()) == 1
    assert first_trip(db).status == "alerted"
    assert first_trip(db).alerted_at is not None
    assert len(outbox) == 1 and outbox[0][0] == "mom@example.com"
    entry = logs(db)[0]
    assert entry.status == "sent" and entry.attempts == 1


def test_safe_trip_never_alerted(client, auth_headers, outbox):
    trip_id = make_trip(client, auth_headers).json()["id"]
    client.post(f"/trips/{trip_id}/safe", headers=auth_headers)
    db = get_session()
    assert check_overdue(db, past_grace()) == 0
    assert outbox == []


def test_alert_sent_only_once(client, auth_headers, outbox):
    make_trip(client, auth_headers)
    db = get_session()
    check_overdue(db, past_grace())
    check_overdue(db, past_grace())
    assert len(outbox) == 1


def test_no_confirmed_buddies_is_logged(client, auth_headers, monkeypatch):
    monkeypatch.setattr("app.alerts.confirmed_buddies", lambda db, user_id: [])
    make_trip(client, auth_headers)
    db = get_session()
    check_overdue(db, past_grace())
    assert first_trip(db).status == "alerted"
    assert logs(db)[0].status == "no_buddies"


def test_failed_send_is_logged_then_retried(client, auth_headers, monkeypatch, outbox):
    calls = {"n": 0}

    def flaky(to, subject, body):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("smtp down")
        outbox.append((to, subject, body))

    monkeypatch.setattr("app.alerts.send_email", flaky)
    make_trip(client, auth_headers)
    db = get_session()
    check_overdue(db, past_grace())
    entry = logs(db)[0]
    assert entry.status == "failed" and "smtp down" in entry.error

    retry_failed(db)
    entry = logs(db)[0]
    assert entry.status == "sent" and entry.attempts == 2
    assert len(outbox) == 1


def test_retry_cancelled_if_traveller_is_safe(client, auth_headers, monkeypatch, outbox):
    def always_fail(to, subject, body):
        raise RuntimeError("smtp down")

    monkeypatch.setattr("app.alerts.send_email", always_fail)
    trip_id = make_trip(client, auth_headers).json()["id"]
    db = get_session()
    check_overdue(db, past_grace())
    client.post(f"/trips/{trip_id}/safe", headers=auth_headers)
    retry_failed(db)
    assert logs(db)[0].status == "cancelled"


def test_deliveries_endpoint_is_private(client, auth_headers, outbox):
    trip_id = make_trip(client, auth_headers).json()["id"]
    check_overdue(get_session(), past_grace())
    r = client.get(f"/trips/{trip_id}/deliveries", headers=auth_headers)
    assert r.status_code == 200 and r.json()[0]["status"] == "sent"
    other = make_user(client, "other@example.com")
    assert client.get(f"/trips/{trip_id}/deliveries", headers=other).status_code == 404


def test_dev_email_prints_when_no_smtp(monkeypatch, capsys):
    monkeypatch.setattr(settings, "smtp_host", "")
    send_email("a@example.com", "Hi", "Body")
    assert "[DEV EMAIL]" in capsys.readouterr().out