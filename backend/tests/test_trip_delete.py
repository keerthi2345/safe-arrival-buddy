from datetime import datetime, timedelta, timezone


def make_trip(client, headers):
    deadline = (datetime.now(timezone.utc) + timedelta(minutes=60)).isoformat()
    return client.post("/trips", json={"label": "Home", "deadline": deadline}, headers=headers)


def make_user(client, email):
    client.post("/auth/register", json={"email": email, "name": "Other", "password": "strongpass123"})
    r = client.post("/auth/login", data={"username": email, "password": "strongpass123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_delete_requires_auth(client):
    assert client.delete("/trips/1").status_code == 401


def test_delete_own_trip(client, auth_headers):
    trip_id = make_trip(client, auth_headers).json()["id"]
    assert client.delete(f"/trips/{trip_id}", headers=auth_headers).status_code == 204
    assert client.get(f"/trips/{trip_id}", headers=auth_headers).status_code == 404
    assert client.get("/trips", headers=auth_headers).json() == []


def test_cannot_delete_other_users_trip(client, auth_headers):
    trip_id = make_trip(client, auth_headers).json()["id"]
    other = make_user(client, "other@example.com")
    assert client.delete(f"/trips/{trip_id}", headers=other).status_code == 404
    assert len(client.get("/trips", headers=auth_headers).json()) == 1
    