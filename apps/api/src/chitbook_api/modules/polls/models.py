from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Identity, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from chitbook_api.core.db import Base, CreatedAtMixin
from chitbook_api.modules.groups.models import ChitGroup
from chitbook_api.modules.users.models import User


class PollStatus(StrEnum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class Poll(CreatedAtMixin, Base):
    __tablename__ = "polls"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    chit_group_id: Mapped[int] = mapped_column(ForeignKey("chit_groups.id", ondelete="CASCADE"), index=True)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    question: Mapped[str] = mapped_column(String(255))
    status: Mapped[PollStatus] = mapped_column(Enum(PollStatus, native_enum=False, length=10))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    group: Mapped[ChitGroup] = relationship(lazy="joined", innerjoin=True)
    creator: Mapped[User] = relationship(lazy="joined", innerjoin=True)
    options: Mapped[list[PollOption]] = relationship(
        back_populates="poll",
        cascade="all, delete-orphan",
        order_by="PollOption.id",
        lazy="selectin",
        passive_deletes=True,
    )


class PollOption(Base):
    __tablename__ = "poll_options"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    poll_id: Mapped[int] = mapped_column(ForeignKey("polls.id", ondelete="CASCADE"), index=True)
    option_text: Mapped[str] = mapped_column(String(255))

    poll: Mapped[Poll] = relationship(back_populates="options")


class PollVote(CreatedAtMixin, Base):
    __tablename__ = "poll_votes"
    __table_args__ = (UniqueConstraint("poll_id", "user_id"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    poll_id: Mapped[int] = mapped_column(ForeignKey("polls.id", ondelete="CASCADE"))
    option_id: Mapped[int] = mapped_column(ForeignKey("poll_options.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
