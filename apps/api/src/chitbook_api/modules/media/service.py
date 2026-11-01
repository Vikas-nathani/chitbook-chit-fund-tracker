"""Photos/videos shared in a group. Stores the link only; files are hosted elsewhere."""

from __future__ import annotations

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from chitbook_api.core.deps import Access
from chitbook_api.core.errors import AppError, ErrorCode
from chitbook_api.modules.groups.service import require_group
from chitbook_api.modules.media.models import GroupMedia
from chitbook_api.modules.media.schemas import MediaCreate, MediaOut

log = structlog.get_logger("chitbook.media")


def to_out(m: GroupMedia) -> MediaOut:
    return MediaOut(
        id=m.id,
        group_id=m.chit_group_id,
        uploader_id=m.uploaded_by_id,
        uploader_name=m.uploader.name,
        url=m.url,
        caption=m.caption,
        media_type=m.media_type,
        created_at=m.created_at,
    )


async def create(session: AsyncSession, access: Access, data: MediaCreate) -> MediaOut:
    await require_group(session, data.group_id)
    await access.require_group_member(data.group_id)
    media = GroupMedia(
        chit_group_id=data.group_id,
        uploaded_by_id=access.user.id,
        url=str(data.url),
        caption=data.caption.strip(),
        media_type=data.media_type,
    )
    session.add(media)
    await session.flush()
    await session.refresh(media)
    log.info("media.shared", media_id=media.id, group_id=data.group_id)
    return to_out(media)


async def list_for_group(session: AsyncSession, access: Access, group_id: int) -> list[MediaOut]:
    await access.require_group_member(group_id)
    stmt = (
        select(GroupMedia).where(GroupMedia.chit_group_id == group_id).order_by(GroupMedia.created_at.desc())
    )
    return [to_out(m) for m in (await session.scalars(stmt)).all()]


async def delete(session: AsyncSession, access: Access, media_id: int) -> None:
    """The uploader or a group admin can delete."""
    media = await session.get(GroupMedia, media_id)
    if media is None:
        raise AppError(ErrorCode.MEDIA_NOT_FOUND)
    if media.uploaded_by_id != access.user.id:
        await access.require_group_admin(media.chit_group_id)
    await session.delete(media)
    log.info("media.deleted", media_id=media_id)
