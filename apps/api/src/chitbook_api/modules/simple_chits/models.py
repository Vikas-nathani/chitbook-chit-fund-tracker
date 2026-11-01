from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from chitbook_api.core.db import Base, TimestampMixin

MONEY = Numeric(14, 2)
PERCENT = Numeric(5, 2)


class SimpleChit(TimestampMixin, Base):
    __tablename__ = "simple_chits"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    total_amount: Mapped[Decimal] = mapped_column(MONEY)
    months: Mapped[int] = mapped_column(Integer)
    start_month: Mapped[str] = mapped_column(String(7))  # yyyy-MM
    per_share_amount: Mapped[Decimal] = mapped_column(MONEY)
    commission_percent: Mapped[Decimal] = mapped_column(PERCENT)
    escalation_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    escalation_percent: Mapped[Decimal] = mapped_column(PERCENT)

    members: Mapped[list[SimpleChitMember]] = relationship(
        back_populates="chit",
        cascade="all, delete-orphan",
        order_by="SimpleChitMember.position",
        lazy="selectin",
        passive_deletes=True,
    )
    payouts: Mapped[list[SimpleChitPayout]] = relationship(
        back_populates="chit",
        cascade="all, delete-orphan",
        order_by="SimpleChitPayout.month_index",
        lazy="selectin",
        passive_deletes=True,
    )


class SimpleChitMember(Base):
    __tablename__ = "simple_chit_members"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    chit_id: Mapped[int] = mapped_column(ForeignKey("simple_chits.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    position: Mapped[int] = mapped_column(Integer)
    shares: Mapped[int] = mapped_column(Integer, default=1)
    start_month_index: Mapped[int] = mapped_column(Integer, default=1)  # 1-based month the member joins

    chit: Mapped[SimpleChit] = relationship(back_populates="members")
    entries: Mapped[list[SimpleChitEntry]] = relationship(
        back_populates="member",
        cascade="all, delete-orphan",
        order_by="SimpleChitEntry.month_index",
        lazy="selectin",
        passive_deletes=True,
    )


class SimpleChitEntry(Base):
    """What one member owes (and whether they paid) for one month."""

    __tablename__ = "simple_chit_entries"
    __table_args__ = (UniqueConstraint("member_id", "month_index"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("simple_chit_members.id", ondelete="CASCADE"))
    month_index: Mapped[int] = mapped_column(Integer)
    amount: Mapped[Decimal] = mapped_column(MONEY)
    paid: Mapped[bool] = mapped_column(Boolean, default=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    member: Mapped[SimpleChitMember] = relationship(back_populates="entries")


class SimpleChitPayout(Base):
    """The pot given to one member in one month."""

    __tablename__ = "simple_chit_payouts"
    __table_args__ = (UniqueConstraint("chit_id", "month_index"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    chit_id: Mapped[int] = mapped_column(ForeignKey("simple_chits.id", ondelete="CASCADE"))
    month_index: Mapped[int] = mapped_column(Integer)
    member_id: Mapped[int] = mapped_column(
        ForeignKey("simple_chit_members.id", ondelete="CASCADE"), index=True
    )
    amount: Mapped[Decimal] = mapped_column(MONEY)
    paid_on: Mapped[date] = mapped_column(Date)
    # Exact amount added to the taker's later months; reversed exactly when the payout changes
    escalation_applied: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"))

    chit: Mapped[SimpleChit] = relationship(back_populates="payouts")
    member: Mapped[SimpleChitMember] = relationship(lazy="selectin")
