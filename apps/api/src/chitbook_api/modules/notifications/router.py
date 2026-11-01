from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, status

from chitbook_api.core.deps import AccessDep, SessionDep
from chitbook_api.core.errors import AUTHED, ErrorCode, errors
from chitbook_api.modules.notifications import service
from chitbook_api.modules.notifications.schemas import (
    ConfigCreate,
    ConfigOut,
    ConfigUpdate,
    NotificationOut,
    UnreadCount,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])

GROUP_ADMIN = (ErrorCode.NOT_GROUP_MEMBER, ErrorCode.NOT_GROUP_ADMIN)


@router.get(
    "/user/{user_id}",
    response_model=list[NotificationOut],
    summary="A user's notifications",
    responses=errors(*AUTHED, ErrorCode.VALIDATION_ERROR, ErrorCode.FORBIDDEN),
)
async def list_notifications(
    user_id: int,
    session: SessionDep,
    access: AccessDep,
    unread_only: Annotated[bool, Query(alias="unreadOnly")] = False,
) -> object:
    return await service.list_for_user(session, access, user_id, unread_only)


@router.get(
    "/user/{user_id}/unread-count",
    response_model=UnreadCount,
    summary="Unread notification count",
    responses=errors(*AUTHED, ErrorCode.VALIDATION_ERROR, ErrorCode.FORBIDDEN),
)
async def unread_count(user_id: int, session: SessionDep, access: AccessDep) -> UnreadCount:
    return UnreadCount(count=await service.unread_count(session, access, user_id))


@router.put(
    "/{notification_id}/read",
    response_model=NotificationOut,
    summary="Mark a notification read",
    responses=errors(
        *AUTHED, ErrorCode.VALIDATION_ERROR, ErrorCode.NOTIFICATION_NOT_FOUND, ErrorCode.FORBIDDEN
    ),
)
async def mark_read(notification_id: int, session: SessionDep, access: AccessDep) -> object:
    return await service.mark_read(session, access, notification_id)


@router.post(
    "/configs",
    response_model=ConfigOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create or replace a group reminder rule",
    responses=errors(*AUTHED, ErrorCode.VALIDATION_ERROR, *GROUP_ADMIN),
)
async def upsert_config(body: ConfigCreate, session: SessionDep, access: AccessDep) -> object:
    return await service.upsert_config(session, access, body)


@router.get(
    "/configs/group/{group_id}",
    response_model=list[ConfigOut],
    summary="A group's reminder rules",
    responses=errors(*AUTHED, ErrorCode.VALIDATION_ERROR, *GROUP_ADMIN),
)
async def list_configs(group_id: int, session: SessionDep, access: AccessDep) -> object:
    return await service.list_configs(session, access, group_id)


@router.patch(
    "/configs/{config_id}",
    response_model=ConfigOut,
    summary="Update a reminder rule",
    responses=errors(
        *AUTHED, ErrorCode.VALIDATION_ERROR, ErrorCode.NOTIFICATION_CONFIG_NOT_FOUND, *GROUP_ADMIN
    ),
)
async def update_config(config_id: int, body: ConfigUpdate, session: SessionDep, access: AccessDep) -> object:
    return await service.update_config(session, access, config_id, body)
