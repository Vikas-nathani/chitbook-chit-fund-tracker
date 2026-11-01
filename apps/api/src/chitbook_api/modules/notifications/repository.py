from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from chitbook_api.modules.notifications.models import Notification, NotificationConfig, NotificationStatus


async def list_for_user(session: AsyncSession, user_id: int, unread_only: bool) -> Sequence[Notification]:
    stmt = (
        select(Notification).where(Notification.user_id == user_id).order_by(Notification.created_at.desc())
    )
    if unread_only:
        stmt = stmt.where(Notification.status == NotificationStatus.UNREAD)
    return (await session.scalars(stmt)).all()


async def count_unread(session: AsyncSession, user_id: int) -> int:
    stmt = (
        select(func.count())
        .select_from(Notification)
        .where(Notification.user_id == user_id, Notification.status == NotificationStatus.UNREAD)
    )
    return int(await session.scalar(stmt) or 0)


async def get_config_by_type(
    session: AsyncSession, group_id: int, notification_type: str
) -> NotificationConfig | None:
    return await session.scalar(
        select(NotificationConfig).where(
            NotificationConfig.chit_group_id == group_id,
            NotificationConfig.notification_type == notification_type,
        )
    )


async def list_configs(session: AsyncSession, group_id: int) -> Sequence[NotificationConfig]:
    stmt = (
        select(NotificationConfig)
        .where(NotificationConfig.chit_group_id == group_id)
        .order_by(NotificationConfig.id)
    )
    return (await session.scalars(stmt)).all()
