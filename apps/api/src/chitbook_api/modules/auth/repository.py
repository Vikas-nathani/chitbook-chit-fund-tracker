from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

from fastapi import Request
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from chitbook_api.core.time import now
from chitbook_api.modules.auth.models import AuthAuditLog, AuthEvent, AuthSession


def client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def user_agent(request: Request) -> str | None:
    ua = request.headers.get("user-agent")
    return ua[:300] if ua else None


async def record_event(
    session: AsyncSession,
    request: Request,
    event: AuthEvent,
    *,
    user_id: int | None = None,
    username: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    session.add(
        AuthAuditLog(
            user_id=user_id,
            username=username,
            event=event.value,
            ip_address=client_ip(request),
            user_agent=user_agent(request),
            details=details,
        )
    )


async def get_by_token_hash(session: AsyncSession, token_hash: str) -> AuthSession | None:
    return await session.scalar(
        select(AuthSession).where(AuthSession.token_hash == token_hash).with_for_update()
    )


async def revoke_family(session: AsyncSession, user_id: int, family_id: uuid.UUID, reason: str) -> int:
    result = await session.execute(
        update(AuthSession)
        .where(
            AuthSession.user_id == user_id,
            AuthSession.family_id == family_id,
            AuthSession.revoked_at.is_(None),
        )
        .values(revoked_at=now(), revoke_reason=reason)
    )
    return result.rowcount  # type: ignore[attr-defined, no-any-return]


async def list_active(session: AsyncSession, user_id: int) -> Sequence[tuple[AuthSession, Any]]:
    """Active sessions with the time each device first signed in (start of its family)."""
    family_start = (
        select(AuthSession.family_id, func.min(AuthSession.created_at).label("signed_in_at"))
        .where(AuthSession.user_id == user_id)
        .group_by(AuthSession.family_id)
        .subquery()
    )
    stmt = (
        select(AuthSession, family_start.c.signed_in_at)
        .join(family_start, family_start.c.family_id == AuthSession.family_id)
        .where(
            AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None), AuthSession.expires_at > now()
        )
        .order_by(AuthSession.last_used_at.desc().nulls_last())
    )
    return [(row[0], row[1]) for row in (await session.execute(stmt)).all()]
