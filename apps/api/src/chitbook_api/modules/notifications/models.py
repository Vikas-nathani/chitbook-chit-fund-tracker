from __future__ import annotations

from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    Boolean,
    Enum,
    ForeignKey,
    Identity,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from chitbook_api.core.db import Base, CreatedAtMixin, TimestampMixin
from chitbook_api.modules.users.models import User


class NotificationStatus(StrEnum):
    UNREAD = "UNREAD"
    READ = "READ"


class Notification(CreatedAtMixin, Base):
    __tablename__ = "notifications"
    __table_args__ = (Index("ix_notifications_user_status", "user_id", "status"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    message: Mapped[str] = mapped_column(String(250))
    type: Mapped[str] = mapped_column(String(30))  # JOIN_REQUEST, PAYMENT_REMINDER, LOAN_DUE, ...
    status: Mapped[NotificationStatus] = mapped_column(Enum(NotificationStatus, native_enum=False, length=10))

    user: Mapped[User] = relationship(lazy="joined", innerjoin=True)


class NotificationConfig(TimestampMixin, Base):
    """Reminder rule for a group, one per (group, notification type)."""

    __tablename__ = "notification_configs"
    __table_args__ = (UniqueConstraint("chit_group_id", "notification_type"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    chit_group_id: Mapped[int] = mapped_column(ForeignKey("chit_groups.id", ondelete="CASCADE"))
    notification_type: Mapped[str] = mapped_column(String(50))
    advance_days: Mapped[int] = mapped_column(Integer)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    message_template: Mapped[str | None] = mapped_column(String(500))
    recurring_day: Mapped[int | None] = mapped_column(Integer)  # day of month, 1-31
