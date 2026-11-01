"""User registration, profile and password management."""

from __future__ import annotations

from collections.abc import Sequence

import structlog
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from chitbook_api.core.deps import Access
from chitbook_api.core.errors import AppError, ErrorCode
from chitbook_api.core.security import hash_password, validate_password_strength, verify_password
from chitbook_api.core.time import now
from chitbook_api.modules.auth.models import AuthSession
from chitbook_api.modules.users import repository
from chitbook_api.modules.users.models import User, UserRole
from chitbook_api.modules.users.schemas import PasswordChange, UserCreate, UserUpdate

log = structlog.get_logger("chitbook.users")


async def register(session: AsyncSession, data: UserCreate, role: UserRole = UserRole.MEMBER) -> User:
    """Creates a user. Public sign-up always gets MEMBER, whatever the request says."""
    username = data.username.strip().lower()
    validate_password_strength(data.password, username)
    if await repository.get_by_username(session, username):
        raise AppError(ErrorCode.USERNAME_TAKEN)
    if await repository.get_by_email(session, data.email):
        raise AppError(ErrorCode.EMAIL_TAKEN)

    user = User(
        name=data.name.strip(),
        username=username,
        email=str(data.email).strip().lower(),
        phone=data.phone,
        password_hash=hash_password(data.password),
        role=role,
        failed_login_count=0,
    )
    session.add(user)
    await session.flush()
    await session.refresh(user)
    log.info("user.registered", new_user_id=user.id, username=user.username, role=user.role.value)
    return user


async def get(session: AsyncSession, access: Access, user_id: int) -> User:
    access.require_self_or_platform_admin(user_id)
    user = await repository.get_by_id(session, user_id)
    if user is None:
        raise AppError(ErrorCode.USER_NOT_FOUND)
    return user


async def get_by_username(session: AsyncSession, access: Access, username: str) -> User:
    user = await repository.get_by_username(session, username)
    if user is None:
        raise AppError(ErrorCode.USER_NOT_FOUND)
    access.require_self_or_platform_admin(user.id)
    return user


async def list_visible(session: AsyncSession, access: Access) -> Sequence[User]:
    if access.is_platform_admin:
        return await repository.list_all(session)
    return await repository.list_visible_to(session, access.user.id)


async def update_profile(session: AsyncSession, access: Access, user_id: int, data: UserUpdate) -> User:
    user = await get(session, access, user_id)
    if data.name is not None:
        user.name = data.name.strip()
    if data.phone is not None:
        user.phone = data.phone
    if data.email is not None:
        existing = await repository.get_by_email(session, data.email)
        if existing is not None and existing.id != user.id:
            raise AppError(ErrorCode.EMAIL_TAKEN)
        user.email = str(data.email).strip().lower()
    await session.flush()
    await session.refresh(user)
    log.info("user.updated", target_user_id=user.id)
    return user


async def change_password(session: AsyncSession, access: Access, user_id: int, data: PasswordChange) -> None:
    """Changes the password and signs out every other device of that user."""
    user = await get(session, access, user_id)
    if not verify_password(data.current_password, user.password_hash):
        raise AppError(ErrorCode.AUTH_WRONG_CURRENT_PASSWORD)
    validate_password_strength(data.new_password, user.username)
    user.password_hash = hash_password(data.new_password)
    await session.execute(
        update(AuthSession)
        .where(AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None))
        .values(revoked_at=now(), revoke_reason="PASSWORD_CHANGED")
    )
    log.info("user.password_changed", target_user_id=user.id)


async def delete(session: AsyncSession, access: Access, user_id: int) -> None:
    user = await get(session, access, user_id)
    await session.delete(user)
    log.info("user.deleted", target_user_id=user_id)
