from __future__ import annotations

import secrets
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Identity,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from chitbook_api.core.db import Base, TimestampMixin
from chitbook_api.modules.users.models import User


class GroupStatus(StrEnum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    INACTIVE = "INACTIVE"


class MembershipStatus(StrEnum):
    PENDING = "PENDING"  # asked to join by code, waiting for a group admin
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"


class GroupRole(StrEnum):
    ADMIN = "ADMIN"
    MEMBER = "MEMBER"


def new_group_code() -> str:
    return "CHIT" + secrets.token_hex(3).upper()  # e.g. CHIT3F5A7C


class ChitGroup(TimestampMixin, Base):
    __tablename__ = "chit_groups"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    group_code: Mapped[str] = mapped_column(String(20), unique=True, default=new_group_code)
    name: Mapped[str] = mapped_column(String(100))
    duration: Mapped[int] = mapped_column(Integer)  # months
    monthly_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    total_members: Mapped[int] = mapped_column(Integer)  # member limit
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[GroupStatus] = mapped_column(Enum(GroupStatus, native_enum=False, length=20))


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("user_id", "chit_group_id"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    chit_group_id: Mapped[int] = mapped_column(ForeignKey("chit_groups.id", ondelete="CASCADE"), index=True)
    join_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[MembershipStatus] = mapped_column(Enum(MembershipStatus, native_enum=False, length=20))
    role: Mapped[GroupRole] = mapped_column(Enum(GroupRole, native_enum=False, length=20))

    user: Mapped[User] = relationship(lazy="joined", innerjoin=True)
    group: Mapped[ChitGroup] = relationship(lazy="joined", innerjoin=True)
