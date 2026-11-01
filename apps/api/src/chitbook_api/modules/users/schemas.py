from __future__ import annotations

from pydantic import EmailStr, Field

from chitbook_api.core.schemas import ApiModel, AppDateTime
from chitbook_api.modules.users.models import UserRole

USERNAME_PATTERN = r"^[A-Za-z0-9._-]{3,30}$"
PHONE_PATTERN = r"^\+?[0-9]{10,15}$"


class UserOut(ApiModel):
    id: int
    name: str
    username: str
    phone: str | None
    email: str
    role: UserRole
    created_at: AppDateTime
    updated_at: AppDateTime


class UserCreate(ApiModel):
    name: str = Field(min_length=1, max_length=100)
    username: str = Field(pattern=USERNAME_PATTERN, description="3-30 letters, digits, . _ -")
    email: EmailStr
    phone: str | None = Field(default=None, pattern=PHONE_PATTERN)
    password: str = Field(min_length=1, max_length=128)


class UserUpdate(ApiModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    phone: str | None = Field(default=None, pattern=PHONE_PATTERN)
    email: EmailStr | None = None


class PasswordChange(ApiModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=1, max_length=128)
