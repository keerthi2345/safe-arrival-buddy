USER = {"email": "Asha@Example.com", "name": "Asha", "password": "strongpass123"}


def register(client, **overrides):
    return client.post("/auth/register", json={**USER, **overrides})


def login(client, email="asha@example.com", password="strongpass123"):
    return client.post("/auth/login", data={"username": email, "password": password})


def test_register_success(client):
    r = register(client)
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "asha@example.com"  # normalised to lowercase
    assert "password" not in body and "password_hash" not in body


def test_register_duplicate_email(client):
    register(client)
    assert register(client).status_code == 409


def test_register_short_password(client):
    assert register(client, password="short").status_code == 422


def test_register_bad_email(client):
    assert register(client, email="not-an-email").status_code == 422


def test_login_success_returns_token(client):
    register(client)
    r = login(client)
    assert r.status_code == 200
    assert r.json()["token_type"] == "bearer"
    assert r.json()["access_token"]


def test_login_wrong_password(client):
    register(client)
    assert login(client, password="wrongpass999").status_code == 401


def test_login_unknown_email(client):
    assert login(client, email="nobody@example.com").status_code == 401