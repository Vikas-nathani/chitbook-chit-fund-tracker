"""In-app notifications and per-group reminder rules."""

from __future__ import annotations

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from chitbook_api.core.deps import Access
from chitbook_api.core.errors import AppError, ErrorCode
from chitbook_api.modules.notifications import repository
from chitbook_api.modules.notifications.models import Notification, NotificationConfig, NotificationStatus
from chitbook_api.modules.notifications.schemas import ConfigCreate, ConfigOut, ConfigUpdate, NotificationOut

log = structlog.get_logger("chitbook.notifications")


def to_out(n: Notification) -> NotificationOut:
    return NotificationOut(
        id=n.id, message=n.message, type=n.type, status=n.status, user_id=n.user_id, user_name=n.user.name,
        created_at=n.created_at,
    )  # fmt: skip


async def create_notification(session: AsyncSession, user_id: int, message: str, type_: str) -> None:
    """Used by other modules (e.g. a join request notifies the group admins)."""
    session.add(
        Notification(user_id=user_id, message=message[:250], type=type_, status=NotificationStatus.UNREAD)
    )
    log.info("notification.created", recipient_user_id=user_id, type=type_)


async def list_for_user(
    session: AsyncSession, access: Access, user_id: int, unread_only: bool
) -> list[NotificationOut]:
    access.require_self_or_platform_admin(user_id)
    return [to_out(n) for n in await repository.list_for_user(session, user_id, unread_only)]


async def unread_count(session: AsyncSession, access: Access, user_id: int) -> int:
    access.require_self_or_platform_admin(user_id)
    return await repository.count_unread(session, user_id)


async def mark_read(session: AsyncSession, access: Access, notification_id: int) -> NotificationOut:
    notification = await session.get(Notification, notification_id)
    if notification is None:
        raise AppError(ErrorCode.NOTIFICATION_NOT_FOUND)
    access.require_self_or_platform_admin(notification.user_id)
    notification.status = NotificationStatus.READ
    await session.flush()
    return to_out(notification)


async def upsert_config(session: AsyncSession, access: Access, data: ConfigCreate) -> ConfigOut:
    """Creates the rule, or replaces it if the group already has one of that type."""
    from chitbook_api.modules.groups.service import require_group  # local import avoids a cycle

    await require_group(session, data.chit_group_id)
    await access.require_group_admin(data.chit_group_id)
    config = await repository.get_config_by_type(session, data.chit_group_id, data.notification_type)
    if config is None:
        config = NotificationConfig(
            chit_group_id=data.chit_group_id, notification_type=data.notification_type
        )
        session.add(config)
    config.advance_days = data.advance_days
    config.enabled = data.enabled
    config.message_template = data.message_template
    config.recurring_day = data.recurring_day
    await session.flush()
    await session.refresh(config)
    log.info("notification_config.saved", group_id=data.chit_group_id, type=data.notification_type)
    return ConfigOut.model_validate(config)


async def list_configs(session: AsyncSession, access: Access, group_id: int) -> list[ConfigOut]:
    await access.require_group_admin(group_id)
    return [ConfigOut.model_validate(c) for c in await repository.list_configs(session, group_id)]


async def update_config(
    session: AsyncSession, access: Access, config_id: int, data: ConfigUpdate
) -> ConfigOut:
    config = await session.get(NotificationConfig, config_id)
    if config is None:
        raise AppError(ErrorCode.NOTIFICATION_CONFIG_NOT_FOUND)
    await access.require_group_admin(config.chit_group_id)
    for field in ("advance_days", "enabled", "message_template", "recurring_day"):
        value = getattr(data, field)
        if value is not None:
            setattr(config, field, value)
    await session.flush()
    await session.refresh(config)
    log.info("notification_config.updated", config_id=config_id)
    return ConfigOut.model_validate(config)
