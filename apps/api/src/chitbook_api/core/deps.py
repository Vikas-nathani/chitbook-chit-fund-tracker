"""Request dependencies: DB session, current user (from the access token), access control."""

from __future__ import annotations

from typing import Annotated

import structlog
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from chitbook_api.core.db import get_session
from chitbook_api.core.errors import AppError, ErrorCode
from chitbook_api.core.security import AccessClaims, decode_access_token
from chitbook_api.core.time import now
from chitbook_api.modules.auth.models import AuthSession
from chitbook_api.modules.groups.models import GroupRole, Membership, MembershipStatus
from chitbook_api.modules.users.models import User, UserRole

# scope="function": the transaction commits when the endpoint returns, *before* the response is
# sent. Without it the client could get 200 and send its next request before the commit lands
# (e.g. refresh right after login), and a failing commit would be hidden behind a 200.
SessionDep = Annotated[AsyncSession, Depends(get_session, scope="function")]

_bearer = HTTPBearer(auto_error=False, description="Access token from POST /api/v1/auth/login")


async def get_current_user(
    request: Request,
    session: SessionDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    """Validates the bearer access token and returns the signed-in user.

    Also checks the token's session family is still active, so "log out" and
    "sign out this device" take effect immediately, not when the token expires.
    """
    if credentials is None:
        raise AppError(ErrorCode.AUTH_REQUIRED)
    user, claims = await authenticate_token(session, credentials.credentials)
    request.state.session_family = claims.session_family
    structlog.contextvars.bind_contextvars(user_id=user.id)
    return user


async def authenticate_token(session: AsyncSession, token: str) -> tuple[User, AccessClaims]:
    """Shared by HTTP requests and the chat WebSocket."""
    claims = decode_access_token(token)
    session_active = await session.scalar(
        select(
            exists().where(
                AuthSession.family_id == claims.session_family,
                AuthSession.user_id == claims.user_id,
                AuthSession.revoked_at.is_(None),
                AuthSession.expires_at > now(),
            )
        )
    )
    if not session_active:
        raise AppError(ErrorCode.AUTH_SESSION_REVOKED)

    user = await session.get(User, claims.user_id)
    if user is None:
        raise AppError(ErrorCode.AUTH_TOKEN_INVALID)
    return user, claims


CurrentUser = Annotated[User, Depends(get_current_user)]


class Access:
    """Authorization checks, mirroring the rules every service relies on.

    - Platform ADMIN passes every check.
    - Group checks require an ACTIVE membership (and the ADMIN group role for admin checks).
    """

    def __init__(self, session: SessionDep, user: CurrentUser) -> None:
        self.session = session
        self.user = user

    @property
    def is_platform_admin(self) -> bool:
        return self.user.role == UserRole.ADMIN

    def require_platform_admin(self) -> None:
        if not self.is_platform_admin:
            raise AppError(ErrorCode.ADMIN_REQUIRED)

    def require_self_or_platform_admin(self, user_id: int) -> None:
        if not (self.is_platform_admin or self.user.id == user_id):
            raise AppError(ErrorCode.FORBIDDEN, "You do not have access to this user's data")

    async def active_membership(self, group_id: int, user_id: int | None = None) -> Membership | None:
        return await self.session.scalar(
            select(Membership).where(
                Membership.user_id == (user_id or self.user.id),
                Membership.chit_group_id == group_id,
                Membership.status == MembershipStatus.ACTIVE,
            )
        )

    async def require_group_member(self, group_id: int) -> Membership | None:
        """Returns the caller's membership (None for platform admins)."""
        if self.is_platform_admin:
            return None
        membership = await self.active_membership(group_id)
        if membership is None:
            raise AppError(ErrorCode.NOT_GROUP_MEMBER)
        return membership

    async def is_group_admin(self, group_id: int) -> bool:
        if self.is_platform_admin:
            return True
        membership = await self.active_membership(group_id)
        return membership is not None and membership.role == GroupRole.ADMIN

    async def require_group_admin(self, group_id: int) -> None:
        if self.is_platform_admin:
            return
        membership = await self.require_group_member(group_id)
        if membership is None or membership.role != GroupRole.ADMIN:
            raise AppError(ErrorCode.NOT_GROUP_ADMIN)

    async def require_self_or_group_admin(self, user_id: int, group_id: int) -> None:
        if self.is_platform_admin:
            return
        if self.user.id == user_id:
            await self.require_group_member(group_id)
            return
        await self.require_group_admin(group_id)


AccessDep = Annotated[Access, Depends(Access)]
