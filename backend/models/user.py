"""User model for authentication."""

from datetime import datetime, timezone
from pydantic import BaseModel, Field


class User(BaseModel):
    id: str
    email: str
    hashed_password: str = Field(exclude=True)
    role: str = "teacher"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class UserPublic(BaseModel):
    id: str
    email: str
    role: str
    created_at: datetime
