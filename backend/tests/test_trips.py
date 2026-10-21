from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.database import get_db
from app.main import app
from app.models import Trip, utcnow


def future(minutes=60):
    return (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()


def make_trip(client, headers, minutes=60, **extra):
    return client.post(
        "/trips", json={"label": "Home", "deadline": future(minutes), **extra}, headers=headers
    )


def make_user(client, email):
    client.post("/auth/register", json={"email": email, "name": "Other", "password": "strongpass123"})
    r = client.post("/auth/login", data={"username": email, "password": "strongpass123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def set_status(status):
    db = next(app.dependency_overrides[get_db]())
    trip = db.scalar(select(Trip))
    trip.status = status
    db.commit()
    db.close()


def test_trips_require_auth(client):
    assert client.get("/trips").status_code == 401
    assert client.post("/trips", json={"deadline": future()}).status_code == 401


def test_create_trip_defaults(client, auth_headers):
    r = make_trip(client, auth_headers)
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "active"
    assert body["grace_minutes"] == 10


def test_custom_grace(client, auth_headers):
    assert make_trip(client, auth_headers, grace_minutes=20).json()["grace_minutes"] == 20


def test_deadline_in_past_rejected(client, auth_headers):
    assert make_trip(client, auth_headers, minutes=-5).status_code == 400


def test_deadline_without_timezone_rejected(client, auth_headers):
    r = client.post("/trips", json={"deadline": "2030-01-01T10:00:00"}, headers=auth_headers)
    assert r.status_code == 422


def test_max_active_trips(client, auth_headers):
    for _ in range(3):
        assert make_trip(client, auth_headers).status_code == 201
    assert make_trip(client, auth_headers).status_code == 400


def test_mark_safe(client, auth_headers):
    trip_id = make_trip(client, auth_headers).json()["id"]
    r = client.post(f"/trips/{trip_id}/safe", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "safe"
    assert r.json()["safe_at"] is not None


def test_mark_safe_twice_rejected(client, auth_headers):
    trip_id = make_trip(client, auth_headers).json()["id"]
    client.post(f"/trips/{trip_id}/safe", headers=auth_headers)
    assert client.post(f"/trips/{trip_id}/safe", headers=auth_headers).status_code == 409


def test_safe_after_alert_is_allowed(client, auth_headers):
    trip_id = make_trip(client, auth_headers).json()["id"]
    set_status("alerted")
    r = client.post(f"/trips/{trip_id}/safe", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "safe"


def test_extend_deadline(client, auth_headers):
    trip_id = make_trip(client, auth_headers, minutes=60).json()["id"]
    r = client.post(f"/trips/{trip_id}/extend", json={"deadline": future(120)}, headers=auth_headers)
    assert r.status_code == 200


def test_extend_to_earlier_rejected(client, auth_headers):
    trip_id = make_trip(client, auth_headers, minutes=60).json()["id"]
    r = client.post(f"/trips/{trip_id}/extend", json={"deadline": future(30)}, headers=auth_headers)
    assert r.status_code == 400


def test_extend_non_active_rejected(client, auth_headers):
    trip_id = make_trip(client, auth_headers).json()["id"]
    client.post(f"/trips/{trip_id}/safe", headers=auth_headers)
    r = client.post(f"/trips/{trip_id}/extend", json={"deadline": future(120)}, headers=auth_headers)
    assert r.status_code == 409


def test_user_cannot_see_other_users_trips(client, auth_headers):
    trip_id = make_trip(client, auth_headers).json()["id"]
    other = make_user(client, "other@example.com")
    assert client.get("/trips", headers=other).json() == []
    assert client.get(f"/trips/{trip_id}", headers=other).status_code == 404


def test_user_cannot_modify_other_users_trips(client, auth_headers):
    trip_id = make_trip(client, auth_headers).json()["id"]
    other = make_user(client, "other@example.com")
    assert client.post(f"/trips/{trip_id}/safe", headers=other).status_code == 404
    r = client.post(f"/trips/{trip_id}/extend", json={"deadline": future(120)}, headers=other)
    assert r.status_code == 404
    assert client.get(f"/trips/{trip_id}", headers=auth_headers).json()["status"] == "active"

def test_deadline_with_offset_is_stored_as_utc(client, auth_headers):
    ist = timezone(timedelta(hours=5, minutes=30))
    local = datetime.now(ist) + timedelta(minutes=60)
    r = client.post("/trips", json={"deadline": local.isoformat()}, headers=auth_headers)
    assert r.status_code == 201
    stored = datetime.fromisoformat(r.json()["deadline"])
    if stored.tzinfo is None:
        stored = stored.replace(tzinfo=timezone.utc)
    assert abs((stored - local).total_seconds()) < 2