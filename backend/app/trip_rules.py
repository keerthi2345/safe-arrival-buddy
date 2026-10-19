from datetime import datetime, timedelta

from fastapi import HTTPException

from .models import Trip, as_utc, utcnow

# The only legal moves. Anything else is refused.
ALLOWED = {
    "active": {"safe", "alerted"},
    "alerted": {"safe", "resolved"},
    "safe": set(),
    "resolved": set(),
}


def transition(trip: Trip, new_status: str) -> None:
    if new_status not in ALLOWED[trip.status]:
        raise HTTPException(409, f"Trip is {trip.status}; cannot change it to {new_status}")
    trip.status = new_status
    if new_status == "safe":
        trip.safe_at = utcnow()
    elif new_status == "alerted":
        trip.alerted_at = utcnow()


def extend_deadline(trip: Trip, new_deadline: datetime) -> None:
    if trip.status != "active":
        raise HTTPException(409, "Only active trips can be extended")
    if as_utc(new_deadline) <= as_utc(trip.deadline):
        raise HTTPException(400, "New deadline must be later than the current one")
    trip.deadline = as_utc(new_deadline)


def alert_time(trip: Trip) -> datetime:
    return as_utc(trip.deadline) + timedelta(minutes=trip.grace_minutes)