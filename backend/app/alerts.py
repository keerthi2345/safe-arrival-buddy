from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .mailer import send_email
from .models import Buddy, DeliveryLog, Trip, User, as_utc, utcnow
from .trip_rules import alert_time, transition
from .watch_links import watch_url


def confirmed_buddies(db: Session, user_id: int):
    """Accepted, not removed, in alert order (priority 1 first)."""
    return db.scalars(
        select(Buddy)
        .where(
            Buddy.user_id == user_id,
            Buddy.confirmed_at.is_not(None),
            Buddy.revoked_at.is_(None),
        )
        .order_by(Buddy.priority, Buddy.id)
    ).all()


def _fmt(dt: datetime) -> str:
    return as_utc(dt).strftime("%d %b %Y, %H:%M UTC")


def alert_message(trip: Trip, user: User, link: str) -> tuple[str, str]:
    label = trip.label or "a trip"
    subject = f"[Safe Arrival] {user.name} has not checked in"
    body = (
        f"{user.name} has not confirmed arrival for: {label}.\n"
        f"Expected by: {_fmt(trip.deadline)} (plus {trip.grace_minutes} min grace).\n"
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
    """Alert the next buddy if nobody has acknowledged within escalation_minutes."""
    now = now or utcnow()
    cutoff = now - settings.escalation_minutes * settings.minute
    escalated = 0
    for trip in db.scalars(select(Trip).where(Trip.status == "alerted")).all():
        logs = [
            entry
            for entry in db.scalars(select(DeliveryLog).where(DeliveryLog.trip_id == trip.id)).all()
            if entry.status != "no_buddies"
        ]
        if not logs:
            continue
        if any(entry.acknowledged_at for entry in logs):
            continue  # a buddy has seen it
        if len(logs) >= settings.max_buddies:
            continue  # everyone has been alerted
        last = max(logs, key=lambda entry: entry.level)
        waited_since = trip.alerted_at if last.level == 1 else last.created_at
        if as_utc(waited_since) > cutoff:
            continue  # not waited long enough
        already = {entry.buddy_email for entry in logs}
        nxt = next((b for b in confirmed_buddies(db, trip.user_id) if b.email not in already), None)
        if nxt is None:
            continue
        log = DeliveryLog(trip_id=trip.id, buddy_email=nxt.email, level=last.level + 1)
        db.add(log)
        db.commit()
        _attempt(db, log, trip, db.get(User, trip.user_id))
        escalated += 1
    return escalated


def run_checks(db: Session) -> None:
    check_overdue(db)
    escalate_unacknowledged(db)
    retry_failed(db)