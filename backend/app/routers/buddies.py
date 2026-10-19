from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..deps import get_current_user
from ..models import Buddy, User, as_utc, utcnow
from ..notifications import send_buddy_confirmation
from ..schemas import BuddyCreate, BuddyOut, ConfirmOut, ConfirmRequest
from ..security import generate_token, hash_token

router = APIRouter(prefix="/buddies", tags=["buddies"])


def _issue_token(buddy: Buddy) -> str:
    raw, hashed = generate_token()
    buddy.confirm_token_hash = hashed
    buddy.confirm_expires_at = utcnow() + timedelta(hours=settings.confirm_token_expire_hours)
    return raw


def _own_active_buddy(db: Session, user: User, buddy_id: int) -> Buddy:
    # 404 (not 403) for other people's buddies, so IDs can't be probed
    buddy = db.scalar(
        select(Buddy).where(
            Buddy.id == buddy_id, Buddy.user_id == user.id, Buddy.revoked_at.is_(None)
        )
    )
    if buddy is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Buddy not found")
    return buddy


@router.post("", response_model=BuddyOut, status_code=status.HTTP_201_CREATED)
def add_buddy(
    data: BuddyCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    email = data.email.lower()
    active = db.scalars(
        select(Buddy).where(Buddy.user_id == user.id, Buddy.revoked_at.is_(None))
    ).all()
    if len(active) >= settings.max_buddies:
        raise HTTPException(400, f"You can have at most {settings.max_buddies} buddies")
    if any(b.email == email for b in active):
        raise HTTPException(409, "This buddy is already added")

    buddy = Buddy(
        user_id=user.id,
        name=data.name,
        email=email,
        priority=max((b.priority for b in active), default=0) + 1,
    )
    raw = _issue_token(buddy)
    db.add(buddy)
    db.commit()
    db.refresh(buddy)
    send_buddy_confirmation(
        to_email=buddy.email, buddy_name=buddy.name, traveller_name=user.name, raw_token=raw
    )
    return buddy


@router.get("", response_model=list[BuddyOut])
def list_buddies(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.scalars(
        select(Buddy)
        .where(Buddy.user_id == user.id, Buddy.revoked_at.is_(None))
        .order_by(Buddy.priority)
    ).all()


@router.post("/{buddy_id}/resend", response_model=BuddyOut)
def resend_confirmation(
    buddy_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    buddy = _own_active_buddy(db, user, buddy_id)
    if buddy.confirmed_at:
        raise HTTPException(409, "This buddy has already confirmed")
    raw = _issue_token(buddy)  # replaces the old token, so the old link dies
    db.commit()
    db.refresh(buddy)
    send_buddy_confirmation(
        to_email=buddy.email, buddy_name=buddy.name, traveller_name=user.name, raw_token=raw
    )
    return buddy


@router.delete("/{buddy_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_buddy(
    buddy_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    buddy = _own_active_buddy(db, user, buddy_id)
    buddy.revoked_at = utcnow()
    buddy.confirm_token_hash = None
    buddy.confirm_expires_at = None
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/confirm", response_model=ConfirmOut)
def confirm_buddy(data: ConfirmRequest, db: Session = Depends(get_db)):
    """Public endpoint: the buddy has no account. The token is the credential."""
    invalid = HTTPException(400, "This confirmation link is invalid or has expired")
    buddy = db.scalar(select(Buddy).where(Buddy.confirm_token_hash == hash_token(data.token)))
    if (
        buddy is None
        or buddy.revoked_at is not None
        or buddy.confirm_expires_at is None
        or as_utc(buddy.confirm_expires_at) < utcnow()
    ):
        raise invalid  # same message for every failure, so nothing leaks

    buddy.confirmed_at = utcnow()
    buddy.confirm_token_hash = None  # single use
    buddy.confirm_expires_at = None
    db.commit()
    traveller = db.get(User, buddy.user_id)
    return ConfirmOut(traveller_name=traveller.name, buddy_name=buddy.name)