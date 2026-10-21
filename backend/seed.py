from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import SessionLocal, engine  # ADJUST if your names differ
from app.main import app
from app.models import Base, Buddy, User, utcnow

DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "demo-pass-123"
BUDDIES = [("Buddy One", "buddy1@example.com"), ("Buddy Two", "buddy2@example.com")]


def main() -> None:
    Base.metadata.create_all(bind=engine)
    client = TestClient(app)

    # already-exists errors are fine, so the script can be run again
    client.post(
        "/auth/register",
        json={"email": DEMO_EMAIL, "name": "Demo Traveller", "password": DEMO_PASSWORD},
    )
    r = client.post("/auth/login", data={"username": DEMO_EMAIL, "password": DEMO_PASSWORD})
    if r.status_code != 200:
        raise SystemExit(f"Could not log in as {DEMO_EMAIL}: {r.status_code} {r.text}")
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

    for name, email in BUDDIES:
        client.post("/buddies", json={"name": name, "email": email}, headers=headers)

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == DEMO_EMAIL))
        for buddy in db.scalars(select(Buddy).where(Buddy.user_id == user.id)):
            if buddy.confirmed_at is None:  # ADJUST: your Buddy's "confirmed" field
                buddy.confirmed_at = utcnow()
        db.commit()

    print("Seeded.")
    print(f"Login: {DEMO_EMAIL} / {DEMO_PASSWORD}")
    print("Confirmed buddies: " + ", ".join(email for _, email in BUDDIES))


if __name__ == "__main__":
    main()