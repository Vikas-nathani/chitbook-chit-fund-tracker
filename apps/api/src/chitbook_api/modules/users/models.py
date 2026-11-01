from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import BigInteger, DateTime, Enum, Identity, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from chitbook_api.core.db import Base, TimestampMixin


class UserRole(StrEnum):
    ADMIN = "ADMIN"  # platform admin: can see and manage everything
    MEMBER = "MEMBER"
    ACCOUNTANT = "ACCOUNTANT"  # can record and verify payments in any group


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    username: Mapped[str] = mapped_column(String(30), unique=True)
    phone: Mapped[str | None] = mapped_column(String(15))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, native_enum=False, length=20, validate_strings=True), default=UserRole.MEMBER
    )
    failed_login_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
