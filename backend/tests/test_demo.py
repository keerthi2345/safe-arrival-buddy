from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.alerts import check_overdue, escalate_unacknowledged
from app.config import settings
from app.models import utcnow
from tests.test_alerts import get_session


@pytest.fixture
def demo_on(monkeypatch):
    monkeypatch.setattr(settings, "demo_mode", True)


@pytest.fixture
def outbox(monkeypatch):
    sent = []
    monkeypatch.setattr(
        "app.alerts.send_email", lambda to, subject, body: sent.append((to, subject, body))
    )
    monkeypatch.setattr(
        "app.alerts.confirmed_buddies",
        lambda db, user_id: [
            SimpleNamespace(email="b1@example.com"),
            SimpleNamespace(email="b2@example.com"),
        ],
    )
    return sent


def test_demo_endpoint_hidden_when_demo_off(client, auth_headers, monkeypatch):
    monkeypatch.setattr(settings, "demo_mode", False)
    assert client.post("/demo/trip", headers=auth_headers).status_code == 404


def test_demo_trip_requires_auth(client, demo_on):
    assert client.post("/demo/trip").status_code == 401


def test_demo_trip_has_short_deadline(client, auth_headers, demo_on):
    r = client.post("/demo/trip", json={"deadline_seconds": 15}, headers=auth_headers)
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "active"
    deadline = datetime.fromisoformat(body["deadline"])
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)
    assert 10 < (deadline - utcnow()).total_seconds() <= 15


def test_demo_alert_fires_within_seconds(client, auth_headers, demo_on, outbox):
    client.post("/demo/trip", json={"deadline_seconds": 15}, headers=auth_headers)
    db = get_session()
    assert check_overdue(db, utcnow() + timedelta(seconds=20)) == 0  # still in grace
    assert check_overdue(db, utcnow() + timedelta(seconds=27)) == 1  # 15s + 10s grace passed
    assert [m[0] for m in outbox] == ["b1@example.com"]


def test_demo_escalation_uses_seconds(client, auth_headers, demo_on, outbox):
    client.post("/demo/trip", json={"deadline_seconds": 5}, headers=auth_headers)
    db = get_session()
    assert check_overdue(db, utcnow() + timedelta(seconds=16)) == 1
    assert escalate_unacknowledged(db, utcnow() + timedelta(seconds=5)) == 0
    assert escalate_unacknowledged(db, utcnow() + timedelta(seconds=11)) == 1
    assert [m[0] for m in outbox] == ["b1@example.com", "b2@example.com"]


def test_demo_mode_scales_time(monkeypatch):
    monkeypatch.setattr(settings, "demo_mode", False)
    assert settings.minute == timedelta(minutes=1)
    assert settings.tick_seconds == settings.check_interval_seconds
    monkeypatch.setattr(settings, "demo_mode", True)
    assert settings.minute == timedelta(seconds=1)
    assert settings.tick_seconds <= 5