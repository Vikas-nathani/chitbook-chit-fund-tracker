from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Identity, Index, String, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from chitbook_api.core.db import Base, CreatedAtMixin


class AuthSession(CreatedAtMixin, Base):
    """One row per issued refresh token.

    A login starts a *family* (= one signed-in device). Each refresh revokes the current row
    and adds a new row in the same family. Presenting an already-rotated token revokes the
    whole family (refresh-token reuse = likely theft).
    """

    __tablename__ = "auth_sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    family_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    device_name: Mapped[str | None] = mapped_column(String(100))
    user_agent: Mapped[str | None] = mapped_column(String(300))
    ip_address: Mapped[str | None] = mapped_column(String(64))
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoke_reason: Mapped[str | None] = mapped_column(String(30))


class AuthEvent(StrEnum):
    REGISTERED = "REGISTERED"
    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    LOGIN_FAILED = "LOGIN_FAILED"
    LOGIN_LOCKED = "LOGIN_LOCKED"
    REFRESHED = "REFRESHED"
    REFRESH_REUSE_DETECTED = "REFRESH_REUSE_DETECTED"
    LOGOUT = "LOGOUT"
    SESSION_REVOKED = "SESSION_REVOKED"
    PASSWORD_CHANGED = "PASSWORD_CHANGED"  # noqa: S105 - event name, not a secret


class AuthAuditLog(CreatedAtMixin, Base):
    __tablename__ = "auth_audit_log"
    __table_args__ = (Index("ix_auth_audit_log_user_created", "user_id", "created_at"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    username: Mapped[str | None] = mapped_column(String(100))
    event: Mapped[str] = mapped_column(String(40))
    ip_address: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(300))
    details: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
