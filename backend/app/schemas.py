from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8, max_length=72)

    @field_validator("password")
    @classmethod
    def password_fits_bcrypt(cls, v: str) -> str:
        # bcrypt only handles 72 bytes; non-ASCII characters take more than 1 byte
        if len(v.encode("utf-8")) > 72:
            raise ValueError("Password is too long (max 72 bytes)")
        return v


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    name: str
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class BuddyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr


class BuddyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    priority: int
    status: str
    confirmed_at: datetime | None
    created_at: datetime


class ConfirmRequest(BaseModel):
    token: str = Field(min_length=10, max_length=200)


class ConfirmOut(BaseModel):
    traveller_name: str
    buddy_name: str

class TripCreate(BaseModel):
    label: str = Field(default="", max_length=100)
    note: str = Field(default="", max_length=500)
    deadline: datetime
    grace_minutes: int | None = Field(default=None, ge=1, le=120)


class TripExtend(BaseModel):
    deadline: datetime


class TripOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    label: str
    note: str
    deadline: datetime
    grace_minutes: int
    status: str
    created_at: datetime
    safe_at: datetime | None
    alerted_at: datetime | None