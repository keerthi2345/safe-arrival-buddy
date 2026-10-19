from datetime import datetime, timedelta, timezone

import jwt

from app.config import settings


def make_token(user_id, expires_in_minutes=60, secret=None):
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes),
    }
    return jwt.encode(payload, secret or settings.secret_key, algorithm=settings.jwt_algorithm)


def test_me_without_token_is_refused(client):
    assert client.get("/me").status_code == 401


def test_me_with_garbage_token_is_refused(client):
    r = client.get("/me", headers={"Authorization": "Bearer not.a.real.token"})
    assert r.status_code == 401


def test_me_with_expired_token_is_refused(client, auth_headers):
    token = make_token(1, expires_in_minutes=-5)
    r = client.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


def test_me_with_wrong_secret_is_refused(client, auth_headers):
    token = make_token(1, secret="x" * 40)
    r = client.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


def test_me_for_deleted_user_is_refused(client, auth_headers):
    token = make_token(9999)  # valid signature, but no such user
    r = client.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


def test_me_with_valid_token(client, auth_headers):
    r = client.get("/me", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == "asha@example.com"
    assert "password_hash" not in body