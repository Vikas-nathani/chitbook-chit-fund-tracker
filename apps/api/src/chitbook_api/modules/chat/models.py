from __future__ import annotations

from sqlalchemy import BigInteger, ForeignKey, Identity, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from chitbook_api.core.db import Base, CreatedAtMixin
from chitbook_api.modules.users.models import User


class ChatMessage(CreatedAtMixin, Base):
    __tablename__ = "chat_messages"
    __table_args__ = (Index("ix_chat_messages_group_id_id", "chit_group_id", "id"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    chit_group_id: Mapped[int] = mapped_column(ForeignKey("chit_groups.id", ondelete="CASCADE"))
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    content: Mapped[str] = mapped_column(String(1000))
    message_type: Mapped[str] = mapped_column(String(20), default="TEXT")

    sender: Mapped[User] = relationship(lazy="joined", innerjoin=True)
