from __future__ import annotations

import asyncio
from typing import Annotated

import structlog
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status

from chitbook_api.core.db import get_sessionmaker
from chitbook_api.core.deps import Access, AccessDep, SessionDep, authenticate_token
from chitbook_api.core.errors import AUTHED, AppError, ErrorCode, errors
from chitbook_api.modules.chat import service
from chitbook_api.modules.chat.hub import hub
from chitbook_api.modules.chat.schemas import ChatMessageOut, SendMessage

router = APIRouter(prefix="/chat", tags=["chat"])
log = structlog.get_logger("chitbook.chat.ws")

AUTH_TIMEOUT_SECONDS = 10
# WebSocket close codes (4000-4999 are application defined)
WS_AUTH_FAILED = 4401
WS_FORBIDDEN = 4403


@router.post(
    "/group/{group_id}/messages",
    response_model=ChatMessageOut,
    status_code=status.HTTP_201_CREATED,
    summary="Send a message to a group",
    responses=errors(
        *AUTHED, ErrorCode.VALIDATION_ERROR, ErrorCode.GROUP_NOT_FOUND, ErrorCode.NOT_GROUP_MEMBER
    ),
)
async def send_message(group_id: int, body: SendMessage, session: SessionDep, access: AccessDep) -> object:
    return await service.send(session, access, group_id, body.content)


@router.get(
    "/group/{group_id}/messages",
    response_model=list[ChatMessageOut],
    summary="Latest messages, or only those after `afterId`",
    responses=errors(*AUTHED, ErrorCode.VALIDATION_ERROR, ErrorCode.NOT_GROUP_MEMBER),
)
async def list_messages(
    group_id: int,
    session: SessionDep,
    access: AccessDep,
    after_id: Annotated[int | None, Query(alias="afterId")] = None,
) -> object:
    return await service.list_messages(session, access, group_id, after_id)


@router.websocket("/ws/groups/{group_id}")
async def chat_socket(ws: WebSocket, group_id: int) -> None:
    """Live chat. Protocol (JSON text frames):

    1. client -> {"type": "auth", "token": "<access token>"}   (within 10 s of connecting)
    2. server -> {"type": "ready"}
    3. client -> {"type": "send", "content": "hello"}           (optional; REST works too)
    4. server -> {"type": "message", "data": ChatMessageOut}    (every new message in the group)
    The token is sent in a message, not the URL, so it never appears in access logs.
    """
    await ws.accept()
    try:
        first = await asyncio.wait_for(ws.receive_json(), timeout=AUTH_TIMEOUT_SECONDS)
        async with get_sessionmaker()() as session:
            user, _ = await authenticate_token(session, str(first.get("token", "")))
            access = Access(session, user)
            await access.require_group_member(group_id)
    except (TimeoutError, ValueError, KeyError, AttributeError, AppError) as exc:
        code = WS_FORBIDDEN if isinstance(exc, AppError) and exc.code.status == 403 else WS_AUTH_FAILED
        log.warning("chat.ws_rejected", group_id=group_id, reason=repr(exc))
        await ws.close(code=code)
        return

    hub.join(group_id, ws)
    structlog.contextvars.bind_contextvars(user_id=user.id)
    log.info("chat.ws_connected", group_id=group_id)
    await ws.send_json({"type": "ready"})
    try:
        while True:
            data = await ws.receive_json()
            if data.get("type") == "send":
                body = SendMessage.model_validate({"content": data.get("content", "")})
                async with get_sessionmaker()() as session:
                    await service.send(session, Access(session, user), group_id, body.content)
                    await session.commit()
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        log.warning("chat.ws_error", group_id=group_id, error=repr(exc))
        await ws.close(code=1011)
    finally:
        hub.leave(group_id, ws)
        log.info("chat.ws_disconnected", group_id=group_id)
