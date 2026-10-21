from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..deps import get_current_user
from ..models import Trip, User, utcnow
from ..schemas import TripOut

router = APIRouter(prefix="/demo", tags=["demo"])


class DemoTripCreate(BaseModel):
    label: str = Field(default="Demo trip", max_length=100)
    deadline_seconds: int = Field(default=15, ge=5, le=600)


@router.post("/trip", response_model=TripOut, status_code=status.HTTP_201_CREATED)
def create_demo_trip(
    data: DemoTripCreate = DemoTripCreate(),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not settings.demo_mode:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    trip = Trip(
        user_id=user.id,
        label=data.label,
        deadline=utcnow() + timedelta(seconds=data.deadline_seconds),
        grace_minutes=settings.default_grace_minutes,
    )
    db.add(trip)
    db.commit()
    db.refresh(trip)
    return trip