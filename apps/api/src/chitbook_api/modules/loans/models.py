from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Identity, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from chitbook_api.core.db import Base, TimestampMixin
from chitbook_api.modules.groups.models import ChitGroup
from chitbook_api.modules.users.models import User


class LoanStatus(StrEnum):
    ACTIVE = "ACTIVE"
    OVERDUE = "OVERDUE"
    PAID = "PAID"
    CLOSED = "CLOSED"


class MemberLoan(TimestampMixin, Base):
    __tablename__ = "member_loans"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    chit_group_id: Mapped[int] = mapped_column(ForeignKey("chit_groups.id", ondelete="CASCADE"), index=True)
    principal: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    interest_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2))  # annual %, simple interest per day
    tenure_months: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    current_payable: Mapped[Decimal] = mapped_column(Numeric(14, 2))  # frozen value once PAID/CLOSED
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[LoanStatus] = mapped_column(Enum(LoanStatus, native_enum=False, length=20))

    user: Mapped[User] = relationship(lazy="joined", innerjoin=True)
    group: Mapped[ChitGroup] = relationship(lazy="joined", innerjoin=True)
