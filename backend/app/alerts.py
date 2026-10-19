from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .delivery import send_email
from .models import Buddy, DeliveryLog, Trip, User, utcnow
from .trip_rules import alert_time, transition


def confirmed_buddies(db: Session, user_id: int):
    # ADJUST: change the confirmed condition to match your Buddy model
    # (e.g. Buddy.confirmed.is_(True) if you use a boolean)
    return db.scalars(
        select(Buddy).where(Buddy.user_id == user_id, Buddy.confirmed_at.is_not(None))
    ).all()


def alert_message(trip: Trip, user: User) -> tuple[str, str]:
    label = trip.label or "a trip"
    subject = f"[Safe Arrival] {user.name} has not checked in"
    body = (
        f"{user.name} has not confirmed arrival for: {label}.\n"
        f"Expected by: {trip.deadline.isoformat()} (plus {trip.grace_minutes} min grace).\n"
    )
    if trip.note:
        body += f"Note from {user.name}: {trip.note}\n"
    body += "Please try to contact them."
    return subject, body


def _attempt(db: Session, log: DeliveryLog, trip: Trip, user: User) -> None:
    log.attempts += 1
    log.last_attempt_at = utcnow()
    try:
        subject, body = alert_message(trip, user)
        send_email(log.buddy_email, subject, body)
        log.status = "sent"
        log.error = ""
    except Exception as exc:
        log.status = "failed"
        log.error = str(exc)[:500]
    db.commit()


def check_overdue(db: Session, now: datetime | None = None) -> int:
    now = now or utcnow()
    trips = db.scalars(select(Trip).where(Trip.status == "active")).all()
    alerted = 0
    for trip in trips:
        if alert_time(trip) > now:
            continue
        transition(trip, "alerted")
        user = db.get(User, trip.user_id)
        buddies = confirmed_buddies(db, trip.user_id)
        if buddies:
            logs = [DeliveryLog(trip_id=trip.id, buddy_email=b.email) for b in buddies]
        else:
            logs = [DeliveryLog(trip_id=trip.id, status="no_buddies")]
        db.add_all(logs)
        db.commit()  # alerted state is saved before any email goes out
        for log in logs:
            if log.status == "pending":
                _attempt(db, log, trip, user)
        alerted += 1
    return alerted


def retry_failed(db: Session) -> int:
    logs = db.scalars(
        select(DeliveryLog).where(
            DeliveryLog.status == "failed",
            DeliveryLog.attempts < settings.max_delivery_attempts,
        )
    ).all()
    for log in logs:
        trip = db.get(Trip, log.trip_id)
        if trip.status != "alerted":
            log.status = "cancelled"  # traveller is safe, no need to alert
            db.commit()
            continue
        _attempt(db, log, trip, db.get(User, trip.user_id))
    return len(logs)


def run_checks(db: Session) -> None:
    check_overdue(db)
    retry_failed(db)