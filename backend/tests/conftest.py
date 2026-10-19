import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.notifications import sent_messages

@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()

@pytest.fixture()
def auth_headers(client):
    """Register a user, log in, and return ready-to-use Authorization headers."""
    client.post(
        "/auth/register",
        json={"email": "asha@example.com", "name": "Asha", "password": "strongpass123"},
    )
    r = client.post(
        "/auth/login",
        data={"username": "asha@example.com", "password": "strongpass123"},
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}

@pytest.fixture(autouse=True)
def clear_outbox():
    sent_messages.clear()