from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Identity, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from chitbook_api.core.db import Base, TimestampMixin
from chitbook_api.modules.groups.models import ChitGroup
from chitbook_api.modules.users.models import User


class EntryType(StrEnum):
    CREDIT = "CREDIT"
    DEBIT = "DEBIT"


class LedgerEntry(TimestampMixin, Base):
    __tablename__ = "ledger_entries"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    chit_group_id: Mapped[int] = mapped_column(ForeignKey("chit_groups.id", ondelete="CASCADE"), index=True)
    entry_type: Mapped[EntryType] = mapped_column(Enum(EntryType, native_enum=False, length=10))
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    entry_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    remark: Mapped[str | None] = mapped_column(String(255))
    reference_id: Mapped[str | None] = mapped_column(String(50))  # id of the related auction/payment

    user: Mapped[User] = relationship(lazy="joined", innerjoin=True)
    group: Mapped[ChitGroup] = relationship(lazy="joined", innerjoin=True)
