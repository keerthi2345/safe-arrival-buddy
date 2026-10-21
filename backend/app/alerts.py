from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .delivery import send_email
from .models import Buddy, DeliveryLog, Trip, User, as_utc, utcnow
from .trip_rules import alert_time, transition
from .watch_links import watch_url


def confirmed_buddies(db: Session, user_id: int):
    # ADJUST: change the confirmed condition to match your Buddy model
    # (e.g. Buddy.confirmed.is_(True) if you use a boolean)
    return db.scalars(
        select(Buddy).where(Buddy.user_id == user_id, Buddy.confirmed_at.is_not(None)).order_by(Buddy.id)
    ).all()


def alert_message(trip: Trip, user: User, link: str) -> tuple[str, str]:
    label = trip.label or "a trip"
    subject = f"[Safe Arrival] {user.name} has not checked in"
    body = (
        f"{user.name} has not confirmed arrival for: {label}.\n"
        f"Expected by: {trip.deadline.isoformat()} (plus {trip.grace_minutes} min grace).\n"
    )
    if trip.note:
        body += f"Note from {user.name}: {trip.note}\n"
    body += f"Live status page (tap 'I've seen this' there): {link}\n"
    body += "Please try to contact them."
    return subject, body


def _attempt(db: Session, log: DeliveryLog, trip: Trip, user: User) -> None:
    log.attempts += 1
    log.last_attempt_at = utcnow()
    try:
        subject, body = alert_message(trip, user, watch_url(log.id))
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
            logs = [DeliveryLog(trip_id=trip.id, buddy_email=buddies[0].email, level=1)]
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


def escalate_unacknowledged(db: Session, now: datetime | None = None) -> int:
    now = now or utcnow()
    cutoff = now - timedelta(minutes=settings.escalation_minutes)
    escalated = 0
    for trip in db.scalars(select(Trip).where(Trip.status == "alerted")).all():
        logs = db.scalars(select(DeliveryLog).where(DeliveryLog.trip_id == trip.id)).all()
        if any(entry.level == 2 for entry in logs):
            continue  # already escalated
        if not any(entry.level == 1 and entry.status != "no_buddies" for entry in logs):
            continue
        if any(entry.acknowledged_at for entry in logs):
            continue  # a buddy has seen it
        if as_utc(trip.alerted_at) > cutoff:
            continue  # not waited long enough
        buddies = confirmed_buddies(db, trip.user_id)
        if len(buddies) < 2:
            continue
        log = DeliveryLog(trip_id=trip.id, buddy_email=buddies[1].email, level=2)
        db.add(log)
        db.commit()
        _attempt(db, log, trip, db.get(User, trip.user_id))
        escalated += 1
    return escalated


def run_checks(db: Session) -> None:
    check_overdue(db)
    escalate_unacknowledged(db)
    retry_failed(db)