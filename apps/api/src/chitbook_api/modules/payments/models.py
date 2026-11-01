from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, ForeignKey, Identity, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from chitbook_api.core.db import Base, TimestampMixin
from chitbook_api.modules.groups.models import ChitGroup
from chitbook_api.modules.users.models import User


class PaymentStatus(StrEnum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


class Payment(TimestampMixin, Base):
    __tablename__ = "payments"
    __table_args__ = (Index("ix_payments_group_user", "chit_group_id", "user_id"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    chit_group_id: Mapped[int] = mapped_column(ForeignKey("chit_groups.id", ondelete="CASCADE"))
    month: Mapped[str] = mapped_column(String(15))
    amount_paid: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    payment_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    mode: Mapped[str] = mapped_column(String(20))  # CASH, UPI, BANK_TRANSFER, ...
    status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus, native_enum=False, length=20))
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verified_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(foreign_keys=[user_id], lazy="joined", innerjoin=True)
    group: Mapped[ChitGroup] = relationship(lazy="joined", innerjoin=True)
    verified_by: Mapped[User | None] = relationship(foreign_keys=[verified_by_id], lazy="joined")
