import re
from datetime import timedelta
from types import SimpleNamespace

import pytest

from app.alerts import check_overdue, escalate_unacknowledged
from app.models import utcnow
from app.watch_links import make_token, parse_token
from tests.test_alerts import get_session, past_grace
from tests.test_trips import make_trip


def after_timeout():
    return utcnow() + timedelta(minutes=11)


def before_timeout():
    return utcnow() + timedelta(minutes=5)


def token_from(body):
    return re.search(r"/watch/(\S+)", body).group(1)


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


def alert_trip(client, auth_headers):
    trip_id = make_trip(client, auth_headers).json()["id"]
    db = get_session()
    check_overdue(db, past_grace())
    return trip_id, db


def test_only_first_buddy_alerted_at_first(client, auth_headers, outbox):
    alert_trip(client, auth_headers)
    assert [m[0] for m in outbox] == ["b1@example.com"]


def test_no_escalation_before_timeout(client, auth_headers, outbox):
    _, db = alert_trip(client, auth_headers)
    assert escalate_unacknowledged(db, before_timeout()) == 0
    assert len(outbox) == 1


def test_escalates_to_second_buddy_once(client, auth_headers, outbox):
    _, db = alert_trip(client, auth_headers)
    assert escalate_unacknowledged(db, after_timeout()) == 1
    assert escalate_unacknowledged(db, after_timeout()) == 0
    assert [m[0] for m in outbox] == ["b1@example.com", "b2@example.com"]


def test_acknowledge_stops_escalation(client, auth_headers, outbox):
    _, db = alert_trip(client, auth_headers)
    token = token_from(outbox[0][2])
    r = client.post(f"/watch/{token}/ack")
    assert r.status_code == 200 and r.json()["acknowledged"] is True
    assert escalate_unacknowledged(db, after_timeout()) == 0
    assert len(outbox) == 1


def test_watch_page_needs_no_login(client, auth_headers, outbox):
    alert_trip(client, auth_headers)
    token = token_from(outbox[0][2])
    r = client.get(f"/watch/{token}")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "alerted" and body["label"] == "Home"
    assert body["acknowledged"] is False
    assert "buddy_email" not in body


def test_invalid_tokens_rejected(client, auth_headers, outbox):
    alert_trip(client, auth_headers)
    token = token_from(outbox[0][2])
    bad = token[:-1] + ("0" if token[-1] != "0" else "1")
    assert client.get(f"/watch/{bad}").status_code == 404
    assert client.get("/watch/abc").status_code == 404
    assert client.post("/watch/999.abc/ack").status_code == 404


def test_ack_after_safe_changes_nothing(client, auth_headers, outbox):
    trip_id, _ = alert_trip(client, auth_headers)
    client.post(f"/trips/{trip_id}/safe", headers=auth_headers)
    token = token_from(outbox[0][2])
    r = client.post(f"/watch/{token}/ack")
    assert r.status_code == 200
    assert r.json()["status"] == "safe" and r.json()["acknowledged"] is False


def test_token_roundtrip():
    assert parse_token(make_token(7)) == 7
    assert parse_token("7.wrong") is None
    assert parse_token("x.y") is None