"""Group chat: active members can read and post; new messages are pushed live over WebSocket."""

from __future__ import annotations

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from chitbook_api.core.deps import Access
from chitbook_api.modules.chat import hub
from chitbook_api.modules.chat.models import ChatMessage
from chitbook_api.modules.chat.schemas import ChatMessageOut
from chitbook_api.modules.groups.service import require_group

log = structlog.get_logger("chitbook.chat")

PAGE_LIMIT = 200


def to_out(m: ChatMessage) -> ChatMessageOut:
    return ChatMessageOut(
        id=m.id, chit_group_id=m.chit_group_id, sender_id=m.sender_id, sender_name=m.sender.name,
        content=m.content, message_type=m.message_type, created_at=m.created_at,
    )  # fmt: skip


async def send(session: AsyncSession, access: Access, group_id: int, content: str) -> ChatMessageOut:
    await require_group(session, group_id)
    await access.require_group_member(group_id)
    message = ChatMessage(
        chit_group_id=group_id, sender_id=access.user.id, content=content.strip(), message_type="TEXT"
    )
    session.add(message)
    await session.flush()
    await session.refresh(message)
    out = to_out(message)
    await hub.publish(session, group_id, out.model_dump(mode="json", by_alias=True))
    log.info("chat.message_sent", group_id=group_id, message_id=message.id)
    return out


async def list_messages(
    session: AsyncSession, access: Access, group_id: int, after_id: int | None
) -> list[ChatMessageOut]:
    """Oldest first. Pass after_id to fetch only messages newer than the last one you have."""
    await access.require_group_member(group_id)
    stmt = select(ChatMessage).where(ChatMessage.chit_group_id == group_id)
    if after_id is not None:
        stmt = stmt.where(ChatMessage.id > after_id).order_by(ChatMessage.id).limit(PAGE_LIMIT)
        rows = (await session.scalars(stmt)).all()
    else:  # latest page, returned oldest first
        stmt = stmt.order_by(ChatMessage.id.desc()).limit(PAGE_LIMIT)
        rows = list(reversed((await session.scalars(stmt)).all()))
    return [to_out(m) for m in rows]
