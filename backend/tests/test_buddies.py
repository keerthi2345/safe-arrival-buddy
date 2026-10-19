from datetime import timedelta

from sqlalchemy import select

from app.database import get_db
from app.main import app
from app.models import Buddy, utcnow
from app.notifications import sent_messages


def add_buddy(client, headers, email="mom@example.com", name="Mom"):
    return client.post("/buddies", json={"name": name, "email": email}, headers=headers)


def make_user(client, email):
    client.post("/auth/register", json={"email": email, "name": "Other", "password": "strongpass123"})
    r = client.post("/auth/login", data={"username": email, "password": "strongpass123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_add_buddy_requires_auth(client):
    r = client.post("/buddies", json={"name": "Mom", "email": "mom@example.com"})
    assert r.status_code == 401


def test_add_buddy_creates_pending_and_sends_email(client, auth_headers):
    r = add_buddy(client, auth_headers)
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "pending"
    assert body["priority"] == 1
    assert "token" not in str(body) and "hash" not in str(body)
    assert len(sent_messages) == 1
    assert sent_messages[0]["to"] == "mom@example.com"


def test_priorities_increment(client, auth_headers):
    add_buddy(client, auth_headers, "a@example.com", "A")
    r = add_buddy(client, auth_headers, "b@example.com", "B")
    assert r.json()["priority"] == 2


def test_duplicate_buddy_rejected(client, auth_headers):
    add_buddy(client, auth_headers)
    assert add_buddy(client, auth_headers).status_code == 409


def test_max_buddies_enforced(client, auth_headers):
    for i in range(5):
        assert add_buddy(client, auth_headers, f"b{i}@example.com", f"B{i}").status_code == 201
    assert add_buddy(client, auth_headers, "b6@example.com", "B6").status_code == 400


def test_confirm_success(client, auth_headers):
    add_buddy(client, auth_headers)
    token = sent_messages[-1]["token"]
    r = client.post("/buddies/confirm", json={"token": token})
    assert r.status_code == 200
    assert r.json()["traveller_name"] == "Asha"
    listed = client.get("/buddies", headers=auth_headers).json()
    assert listed[0]["status"] == "confirmed"


def test_confirm_invalid_token(client):
    r = client.post("/buddies/confirm", json={"token": "x" * 43})
    assert r.status_code == 400


def test_confirm_token_is_single_use(client, auth_headers):
    add_buddy(client, auth_headers)
    token = sent_messages[-1]["token"]
    assert client.post("/buddies/confirm", json={"token": token}).status_code == 200
    assert client.post("/buddies/confirm", json={"token": token}).status_code == 400


def test_confirm_expired_token(client, auth_headers):
    add_buddy(client, auth_headers)
    token = sent_messages[-1]["token"]
    db = next(app.dependency_overrides[get_db]())
    buddy = db.scalar(select(Buddy))
    buddy.confirm_expires_at = utcnow() - timedelta(hours=1)
    db.commit()
    db.close()
    assert client.post("/buddies/confirm", json={"token": token}).status_code == 400


def test_user_sees_only_own_buddies(client, auth_headers):
    add_buddy(client, auth_headers)
    other = make_user(client, "other@example.com")
    assert client.get("/buddies", headers=other).json() == []


def test_cannot_revoke_other_users_buddy(client, auth_headers):
    buddy_id = add_buddy(client, auth_headers).json()["id"]
    other = make_user(client, "other@example.com")
    assert client.delete(f"/buddies/{buddy_id}", headers=other).status_code == 404
    assert len(client.get("/buddies", headers=auth_headers).json()) == 1


def test_revoked_buddy_link_stops_working(client, auth_headers):
    buddy_id = add_buddy(client, auth_headers).json()["id"]
    token = sent_messages[-1]["token"]
    assert client.delete(f"/buddies/{buddy_id}", headers=auth_headers).status_code == 204
    assert client.get("/buddies", headers=auth_headers).json() == []
    assert client.post("/buddies/confirm", json={"token": token}).status_code == 400


def test_resend_replaces_old_token(client, auth_headers):
    buddy_id = add_buddy(client, auth_headers).json()["id"]
    old = sent_messages[-1]["token"]
    assert client.post(f"/buddies/{buddy_id}/resend", headers=auth_headers).status_code == 200
    new = sent_messages[-1]["token"]
    assert new != old
    assert client.post("/buddies/confirm", json={"token": old}).status_code == 400
    assert client.post("/buddies/confirm", json={"token": new}).status_code == 200


def test_resend_after_confirm_rejected(client, auth_headers):
    buddy_id = add_buddy(client, auth_headers).json()["id"]
    client.post("/buddies/confirm", json={"token": sent_messages[-1]["token"]})
    assert client.post(f"/buddies/{buddy_id}/resend", headers=auth_headers).status_code == 409