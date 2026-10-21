from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import DeliveryLog, Trip, User, utcnow
from ..schemas import WatchOut
from ..watch_links import parse_token

router = APIRouter(prefix="/watch", tags=["watch"])


def _load(db: Session, token: str):
    log_id = parse_token(token)
    log = db.get(DeliveryLog, log_id) if log_id is not None else None
    if log is None or log.status == "no_buddies":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Link not found")
    trip = db.get(Trip, log.trip_id)
    user = db.get(User, trip.user_id)
    return log, trip, user


def _out(log: DeliveryLog, trip: Trip, user: User) -> WatchOut:
    return WatchOut(
        traveller_name=user.name,
        label=trip.label,
        note=trip.note,
        deadline=trip.deadline,
        status=trip.status,
        alerted_at=trip.alerted_at,
        safe_at=trip.safe_at,
        acknowledged=log.acknowledged_at is not None,
    )


@router.get("/{token}", response_model=WatchOut)
def view_watch(token: str, db: Session = Depends(get_db)):
    log, trip, user = _load(db, token)
    return _out(log, trip, user)


@router.post("/{token}/ack", response_model=WatchOut)
def acknowledge(token: str, db: Session = Depends(get_db)):
    log, trip, user = _load(db, token)
    if trip.status == "alerted" and log.acknowledged_at is None:
        log.acknowledged_at = utcnow()
        db.commit()
        db.refresh(log)
    return _out(log, trip, user)