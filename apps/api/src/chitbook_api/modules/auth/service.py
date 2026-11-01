"""Login, refresh-token rotation (with reuse detection), logout, lockout and sessions."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

import structlog
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from chitbook_api.core.config import get_settings
from chitbook_api.core.errors import AppError, ErrorCode
from chitbook_api.core.security import (
    create_access_token,
    hash_password,
    hash_refresh_token,
    new_refresh_token,
    password_needs_rehash,
    verify_password,
)
from chitbook_api.core.time import now
from chitbook_api.modules.auth import repository
from chitbook_api.modules.auth.models import AuthEvent, AuthSession
from chitbook_api.modules.auth.schemas import LoginRequest
from chitbook_api.modules.users import repository as users_repo
from chitbook_api.modules.users.models import User

log = structlog.get_logger("chitbook.auth")


@dataclass
class IssuedTokens:
    access_token: str
    expires_in: int
    refresh_token: str
    refresh_expires_at: datetime
    user: User


def _lockout_minutes(failed_count: int) -> int:
    """Lock grows exponentially after the limit: base, 2x base, 4x base ... capped."""
    s = get_settings()
    over = failed_count - s.login_max_failed_attempts
    return int(min(s.login_lockout_base_minutes * (2**over), s.login_lockout_max_minutes))


async def _issue(
    session: AsyncSession, request: Request, user: User, family_id: uuid.UUID, device_name: str | None
) -> IssuedTokens:
    s = get_settings()
    raw, token_hash = new_refresh_token()
    expires_at = now() + timedelta(days=s.refresh_token_ttl_days)
    session.add(
        AuthSession(
            user_id=user.id,
            family_id=family_id,
            token_hash=token_hash,
            device_name=device_name,
            user_agent=repository.user_agent(request),
            ip_address=repository.client_ip(request),
            last_used_at=now(),
            expires_at=expires_at,
        )
    )
    access, expires_in = create_access_token(user.id, user.role.value, family_id)
    return IssuedTokens(access, expires_in, raw, expires_at, user)


async def login(session: AsyncSession, request: Request, data: LoginRequest) -> IssuedTokens:
    s = get_settings()
    username = data.username.strip().lower()
    user = await users_repo.get_by_username(session, username)

    if user is not None and user.locked_until is not None and user.locked_until > now():
        retry_after = int((user.locked_until - now()).total_seconds())
        await repository.record_event(
            session, request, AuthEvent.LOGIN_LOCKED, user_id=user.id, username=username
        )
        await session.commit()
        log.warning("auth.login_locked", username=username, retry_after_s=retry_after)
        raise AppError(ErrorCode.AUTH_ACCOUNT_LOCKED, details={"retryAfterSeconds": retry_after})

    # verify_password runs a full hash even for unknown users, so timing does not reveal them
    if user is None or not verify_password(data.password, user.password_hash if user else None):
        details: dict[str, object] = {"reason": "unknown_user" if user is None else "bad_password"}
        if user is not None:
            user.failed_login_count += 1
            if user.failed_login_count >= s.login_max_failed_attempts:
                minutes = _lockout_minutes(user.failed_login_count)
                user.locked_until = now() + timedelta(minutes=minutes)
                details["lockedMinutes"] = minutes
        await repository.record_event(
            session,
            request,
            AuthEvent.LOGIN_FAILED,
            user_id=user.id if user else None,
            username=username,
            details=details,
        )
        await session.commit()  # keep the counter and audit row even though we raise
        log.warning("auth.login_failed", username=username, **details)
        raise AppError(ErrorCode.AUTH_INVALID_CREDENTIALS)

    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = now()
    if password_needs_rehash(user.password_hash):
        user.password_hash = hash_password(data.password)
    tokens = await _issue(session, request, user, uuid.uuid4(), data.device_name)
    await repository.record_event(
        session, request, AuthEvent.LOGIN_SUCCESS, user_id=user.id, username=username
    )
    log.info("auth.login_success", user_id=user.id, client=data.client.value)
    return tokens


async def refresh(session: AsyncSession, request: Request, raw_token: str | None) -> IssuedTokens:
    if not raw_token:
        raise AppError(ErrorCode.AUTH_REFRESH_INVALID)
    row = await repository.get_by_token_hash(session, hash_refresh_token(raw_token))
    if row is None:
        log.warning("auth.refresh_unknown_token")
        raise AppError(ErrorCode.AUTH_REFRESH_INVALID)

    if row.revoked_at is not None:
        if row.revoke_reason == "ROTATED":
            # An old token came back: someone else may hold the newer one. Kill the whole chain.
            revoked = await repository.revoke_family(session, row.user_id, row.family_id, "REUSE_DETECTED")
            await repository.record_event(
                session,
                request,
                AuthEvent.REFRESH_REUSE_DETECTED,
                user_id=row.user_id,
                details={"familyId": str(row.family_id), "revokedSessions": revoked},
            )
            await session.commit()
            log.warning("auth.refresh_reuse_detected", user_id=row.user_id, family_id=str(row.family_id))
            raise AppError(ErrorCode.AUTH_REFRESH_REUSED)
        raise AppError(ErrorCode.AUTH_REFRESH_INVALID)

    if row.expires_at <= now():
        raise AppError(ErrorCode.AUTH_REFRESH_INVALID)

    user = await users_repo.get_by_id(session, row.user_id)
    if user is None:
        raise AppError(ErrorCode.AUTH_REFRESH_INVALID)

    row.revoked_at = now()
    row.revoke_reason = "ROTATED"
    tokens = await _issue(session, request, user, row.family_id, row.device_name)
    await repository.record_event(session, request, AuthEvent.REFRESHED, user_id=user.id)
    log.info("auth.refreshed", user_id=user.id, family_id=str(row.family_id))
    return tokens


async def logout(session: AsyncSession, request: Request, user: User, family_id: uuid.UUID) -> None:
    await repository.revoke_family(session, user.id, family_id, "LOGOUT")
    await repository.record_event(session, request, AuthEvent.LOGOUT, user_id=user.id)
    log.info("auth.logout", user_id=user.id, family_id=str(family_id))


async def revoke_session(session: AsyncSession, request: Request, user: User, family_id: uuid.UUID) -> None:
    if await repository.revoke_family(session, user.id, family_id, "SIGNED_OUT_REMOTELY") == 0:
        raise AppError(ErrorCode.AUTH_SESSION_NOT_FOUND)
    await repository.record_event(
        session, request, AuthEvent.SESSION_REVOKED, user_id=user.id, details={"familyId": str(family_id)}
    )
    log.info("auth.session_revoked", user_id=user.id, family_id=str(family_id))
