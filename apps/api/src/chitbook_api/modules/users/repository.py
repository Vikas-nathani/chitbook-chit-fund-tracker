from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from chitbook_api.modules.groups.models import Membership, MembershipStatus
from chitbook_api.modules.users.models import User


async def get_by_id(session: AsyncSession, user_id: int) -> User | None:
    return await session.get(User, user_id)


async def get_by_username(session: AsyncSession, username: str) -> User | None:
    return await session.scalar(select(User).where(User.username == username.strip().lower()))


async def get_by_email(session: AsyncSession, email: str) -> User | None:
    return await session.scalar(select(User).where(func.lower(User.email) == email.strip().lower()))


async def list_all(session: AsyncSession) -> Sequence[User]:
    return (await session.scalars(select(User).order_by(User.id))).all()


async def list_visible_to(session: AsyncSession, user_id: int) -> Sequence[User]:
    """Users who share at least one ACTIVE group with `user_id` (including that user)."""
    mine = aliased(Membership)
    theirs = aliased(Membership)
    stmt = (
        select(User)
        .join(theirs, theirs.user_id == User.id)
        .join(mine, mine.chit_group_id == theirs.chit_group_id)
        .where(
            mine.user_id == user_id,
            mine.status == MembershipStatus.ACTIVE,
            theirs.status == MembershipStatus.ACTIVE,
        )
        .distinct()
        .order_by(User.id)
    )
    users = list((await session.scalars(stmt)).all())
    if not any(u.id == user_id for u in users):
        me = await session.get(User, user_id)
        if me is not None:
            users.insert(0, me)
    return users
