from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from chitbook_api.modules.funds.models import Fund
from chitbook_api.modules.groups.models import ChitGroup, GroupRole, Membership, MembershipStatus


async def get_group(session: AsyncSession, group_id: int) -> ChitGroup | None:
    return await session.get(ChitGroup, group_id)


async def get_group_by_code(session: AsyncSession, code: str) -> ChitGroup | None:
    return await session.scalar(select(ChitGroup).where(ChitGroup.group_code == code.strip().upper()))


async def list_groups(
    session: AsyncSession, member_user_id: int | None, name: str | None, status: str | None
) -> Sequence[ChitGroup]:
    """All groups (member_user_id=None) or groups where the user is an ACTIVE member."""
    stmt = select(ChitGroup).order_by(ChitGroup.created_at.desc())
    if member_user_id is not None:
        stmt = stmt.join(Membership, Membership.chit_group_id == ChitGroup.id).where(
            Membership.user_id == member_user_id, Membership.status == MembershipStatus.ACTIVE
        )
    if name:
        stmt = stmt.where(ChitGroup.name.ilike(f"%{name}%"))
    if status:
        stmt = stmt.where(ChitGroup.status == status)
    return (await session.scalars(stmt)).all()


async def fund_ids_for(session: AsyncSession, group_ids: Sequence[int]) -> dict[int, int]:
    if not group_ids:
        return {}
    rows = await session.execute(select(Fund.chit_group_id, Fund.id).where(Fund.chit_group_id.in_(group_ids)))
    return {row[0]: row[1] for row in rows.all()}  # group_id -> fund_id


async def get_membership(session: AsyncSession, user_id: int, group_id: int) -> Membership | None:
    return await session.scalar(
        select(Membership).where(Membership.user_id == user_id, Membership.chit_group_id == group_id)
    )


async def list_members(session: AsyncSession, group_id: int, active_only: bool) -> Sequence[Membership]:
    stmt = select(Membership).where(Membership.chit_group_id == group_id).order_by(Membership.id)
    if active_only:
        stmt = stmt.where(Membership.status == MembershipStatus.ACTIVE)
    return (await session.scalars(stmt)).all()


async def list_user_memberships(session: AsyncSession, user_id: int) -> Sequence[Membership]:
    stmt = select(Membership).where(Membership.user_id == user_id).order_by(Membership.id)
    return (await session.scalars(stmt)).all()


async def count_members(session: AsyncSession, group_id: int, active_only: bool) -> int:
    stmt = select(func.count()).select_from(Membership).where(Membership.chit_group_id == group_id)
    if active_only:
        stmt = stmt.where(Membership.status == MembershipStatus.ACTIVE)
    return int(await session.scalar(stmt) or 0)


async def active_admin_user_ids(session: AsyncSession, group_id: int) -> Sequence[int]:
    stmt = select(Membership.user_id).where(
        Membership.chit_group_id == group_id,
        Membership.role == GroupRole.ADMIN,
        Membership.status == MembershipStatus.ACTIVE,
    )
    return (await session.scalars(stmt)).all()
