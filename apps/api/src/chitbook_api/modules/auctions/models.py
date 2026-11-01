from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, ForeignKey, Identity, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from chitbook_api.core.db import Base, TimestampMixin
from chitbook_api.modules.groups.models import ChitGroup
from chitbook_api.modules.users.models import User


class Auction(TimestampMixin, Base):
    __tablename__ = "auctions"
    __table_args__ = (UniqueConstraint("chit_group_id", "month"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    chit_group_id: Mapped[int] = mapped_column(ForeignKey("chit_groups.id", ondelete="CASCADE"))
    winning_member_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    month: Mapped[str] = mapped_column(String(20))
    winning_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    commission: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    auction_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    remark: Mapped[str | None] = mapped_column(String(200))

    winner: Mapped[User] = relationship(lazy="joined", innerjoin=True)
    group: Mapped[ChitGroup] = relationship(lazy="joined", innerjoin=True)
