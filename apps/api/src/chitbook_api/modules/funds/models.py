from __future__ import annotations

from decimal import Decimal

from sqlalchemy import BigInteger, ForeignKey, Identity, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from chitbook_api.core.db import Base, TimestampMixin
from chitbook_api.modules.groups.models import ChitGroup


class Fund(TimestampMixin, Base):
    """The pooled fund of a chit group (exactly one per group, created with the group)."""

    __tablename__ = "funds"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    chit_group_id: Mapped[int] = mapped_column(ForeignKey("chit_groups.id", ondelete="CASCADE"), unique=True)
    name: Mapped[str] = mapped_column(String(150))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    cycle_period: Mapped[int] = mapped_column(Integer)  # months
    interest_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2))  # annual %

    group: Mapped[ChitGroup] = relationship(lazy="joined", innerjoin=True)
