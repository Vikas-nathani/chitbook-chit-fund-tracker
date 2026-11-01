from __future__ import annotations

from enum import StrEnum

from sqlalchemy import BigInteger, Enum, ForeignKey, Identity, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from chitbook_api.core.db import Base, CreatedAtMixin
from chitbook_api.modules.users.models import User


class MediaType(StrEnum):
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"


class GroupMedia(CreatedAtMixin, Base):
    """A link to a photo/video shared in a group (the file itself is hosted elsewhere)."""

    __tablename__ = "group_media"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    chit_group_id: Mapped[int] = mapped_column(ForeignKey("chit_groups.id", ondelete="CASCADE"), index=True)
    uploaded_by_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    url: Mapped[str] = mapped_column(String(1000))
    caption: Mapped[str] = mapped_column(String(255))
    media_type: Mapped[MediaType] = mapped_column(Enum(MediaType, native_enum=False, length=10))

    uploader: Mapped[User] = relationship(lazy="joined", innerjoin=True)
