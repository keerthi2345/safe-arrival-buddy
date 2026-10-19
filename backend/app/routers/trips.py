from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..deps import get_current_user
from ..models import Trip, User, as_utc, utcnow, DeliveryLog
from ..schemas import TripCreate, TripExtend, TripOut, DeliveryOut
from ..trip_rules import extend_deadline, transition

router = APIRouter(prefix="/trips", tags=["trips"])


def _own_trip(db: Session, user: User, trip_id: int) -> Trip:
    # 404 for other people's trips, so IDs can't be probed
    trip = db.scalar(select(Trip).where(Trip.id == trip_id, Trip.user_id == user.id))
    if trip is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Trip not found")
    return trip


@router.post("", response_model=TripOut, status_code=status.HTTP_201_CREATED)
def create_trip(
    data: TripCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if data.deadline.tzinfo is None:
        raise HTTPException(422, "Deadline must include a timezone, e.g. 2026-10-19T21:15:00+05:30")
    if as_utc(data.deadline) <= utcnow():
        raise HTTPException(400, "Deadline must be in the future")
    active_count = db.scalar(
        select(func.count()).select_from(Trip).where(Trip.user_id == user.id, Trip.status == "active")
    )
    if active_count >= settings.max_active_trips:
        raise HTTPException(400, f"You can have at most {settings.max_active_trips} active trips")

    trip = Trip(
        user_id=user.id,
        label=data.label,
        note=data.note,
        deadline=as_utc(data.deadline),
        grace_minutes=data.grace_minutes or settings.default_grace_minutes,
    )
    db.add(trip)
    db.commit()
    db.refresh(trip)
    return trip


@router.get("", response_model=list[TripOut])
def list_trips(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.scalars(
        select(Trip).where(Trip.user_id == user.id).order_by(Trip.created_at.desc())
    ).all()


@router.get("/{trip_id}", response_model=TripOut)
def get_trip(trip_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _own_trip(db, user, trip_id)


@router.post("/{trip_id}/safe", response_model=TripOut)
def mark_safe(trip_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    trip = _own_trip(db, user, trip_id)
    transition(trip, "safe")
    db.commit()
    db.refresh(trip)
    return trip


@router.post("/{trip_id}/extend", response_model=TripOut)
def extend_trip(
    trip_id: int,
    data: TripExtend,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if data.deadline.tzinfo is None:
        raise HTTPException(422, "Deadline must include a timezone")
    trip = _own_trip(db, user, trip_id)
    extend_deadline(trip, data.deadline)
    db.commit()
    db.refresh(trip)
    return trip

@router.get("/{trip_id}/deliveries", response_model=list[DeliveryOut])
def trip_deliveries(
    trip_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    _own_trip(db, user, trip_id)
    return db.scalars(
        select(DeliveryLog).where(DeliveryLog.trip_id == trip_id).order_by(DeliveryLog.id)
    ).all()