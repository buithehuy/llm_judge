import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

class UserBase(BaseModel):
    email: EmailStr = Field(description="Unique email address of the user")
    full_name: str | None = Field(
        default=None, max_length=255, description="Optional display name"

    )

class UserCreate(UserBase):
    password: str = Field(
        min_length=8,
        max_length=128,
        description="Plant-text password (will be hashed before storage)"
    )

class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=255)
    password: str | None = Field(default=None, min_length=8, max_length=128)


class UserResponse(UserBase):
    id: uuid.UUID
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}