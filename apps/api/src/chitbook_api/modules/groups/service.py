"""Chit groups (auction-style groups with codes) and their memberships."""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from chitbook_api.core.deps import Access
from chitbook_api.core.errors import AppError, ErrorCode
from chitbook_api.core.time import now
from chitbook_api.modules.funds.models import Fund
from chitbook_api.modules.groups import repository
from chitbook_api.modules.groups.models import ChitGroup, GroupRole, GroupStatus, Membership, MembershipStatus
from chitbook_api.modules.groups.schemas import GroupCreate, GroupOut, GroupUpdate, MembershipOut
from chitbook_api.modules.notifications import service as notifications
from chitbook_api.modules.users import repository as users_repo

log = structlog.get_logger("chitbook.groups")


# ---------------------------------------------------------------- mapping


def to_group_out(group: ChitGroup, fund_id: int | None) -> GroupOut:
    return GroupOut(
        id=group.id, group_code=group.group_code, name=group.name, duration=group.duration,
        monthly_amount=group.monthly_amount, total_members=group.total_members, start_date=group.start_date,
        status=group.status, fund_id=fund_id, created_at=group.created_at, updated_at=group.updated_at,
    )  # fmt: skip


def to_membership_out(m: Membership) -> MembershipOut:
    g = m.group
    return MembershipOut(
        id=m.id,
        user_id=m.user_id,
        user_name=m.user.name,
        chit_group_id=g.id,
        chit_group_name=g.name,
        chit_group_code=g.group_code,
        monthly_amount=g.monthly_amount,
        duration=g.duration,
        total_members=g.total_members,
        start_date=g.start_date,
        join_date=m.join_date,
        status=m.status,
        role=m.role,
    )


async def _with_fund(session: AsyncSession, group: ChitGroup) -> GroupOut:
    funds = await repository.fund_ids_for(session, [group.id])
    return to_group_out(group, funds.get(group.id))


async def require_group(session: AsyncSession, group_id: int) -> ChitGroup:
    group = await repository.get_group(session, group_id)
    if group is None:
        raise AppError(ErrorCode.GROUP_NOT_FOUND)
    return group


# ---------------------------------------------------------------- groups


async def create(session: AsyncSession, access: Access, data: GroupCreate) -> GroupOut:
    """Creates the group, its fund, and makes the creator the group's ADMIN."""
    group = ChitGroup(
        name=data.name.strip(),
        duration=data.duration,
        monthly_amount=data.monthly_amount,
        total_members=data.total_members,
        start_date=data.start_date or now(),
        status=GroupStatus.PENDING,
    )
    session.add(group)
    await session.flush()
    fund = Fund(
        chit_group_id=group.id,
        name=f"Fund for {group.name}",
        total_amount=Decimal("0"),
        cycle_period=group.duration,
        interest_rate=Decimal("0"),
    )
    session.add(fund)
    session.add(
        Membership(
            user_id=access.user.id, chit_group_id=group.id, join_date=now(),
            status=MembershipStatus.ACTIVE, role=GroupRole.ADMIN,
        )
    )  # fmt: skip
    await session.flush()
    await session.refresh(group)
    log.info("group.created", group_id=group.id, group_code=group.group_code)
    return to_group_out(group, fund.id)


async def get(session: AsyncSession, access: Access, group_id: int) -> GroupOut:
    group = await require_group(session, group_id)
    await access.require_group_member(group_id)
    return await _with_fund(session, group)


async def get_by_code(session: AsyncSession, access: Access, code: str) -> GroupOut:
    group = await repository.get_group_by_code(session, code)
    if group is None:
        raise AppError(ErrorCode.GROUP_NOT_FOUND)
    await access.require_group_member(group.id)
    return await _with_fund(session, group)


async def list_visible(
    session: AsyncSession, access: Access, name: str | None, status: GroupStatus | None
) -> list[GroupOut]:
    member_id = None if access.is_platform_admin else access.user.id
    groups = await repository.list_groups(session, member_id, name, status.value if status else None)
    funds = await repository.fund_ids_for(session, [g.id for g in groups])
    return [to_group_out(g, funds.get(g.id)) for g in groups]


async def update(session: AsyncSession, access: Access, group_id: int, data: GroupUpdate) -> GroupOut:
    group = await require_group(session, group_id)
    await access.require_group_admin(group_id)
    for field in ("name", "duration", "monthly_amount", "total_members", "start_date"):
        value = getattr(data, field)
        if value is not None:
            setattr(group, field, value.strip() if isinstance(value, str) else value)
    await session.flush()
    await session.refresh(group)
    log.info("group.updated", group_id=group_id)
    return await _with_fund(session, group)


async def set_status(session: AsyncSession, access: Access, group_id: int, status: GroupStatus) -> GroupOut:
    group = await require_group(session, group_id)
    await access.require_group_admin(group_id)
    group.status = status
    await session.flush()
    await session.refresh(group)
    log.info("group.status_changed", group_id=group_id, status=status.value)
    return await _with_fund(session, group)


async def delete(session: AsyncSession, access: Access, group_id: int) -> None:
    group = await require_group(session, group_id)
    await access.require_group_admin(group_id)
    await session.delete(group)  # memberships, fund, payments, ... cascade in the database
    log.info("group.deleted", group_id=group_id)


# ---------------------------------------------------------------- memberships


async def add_member(session: AsyncSession, access: Access, group_id: int, user_id: int) -> MembershipOut:
    group = await require_group(session, group_id)
    await access.require_group_admin(group_id)
    if await users_repo.get_by_id(session, user_id) is None:
        raise AppError(ErrorCode.USER_NOT_FOUND)
    if await repository.get_membership(session, user_id, group_id) is not None:
        raise AppError(ErrorCode.MEMBERSHIP_EXISTS)
    if await repository.count_members(session, group_id, active_only=False) >= group.total_members:
        raise AppError(ErrorCode.GROUP_FULL)
    membership = Membership(
        user_id=user_id, chit_group_id=group_id, join_date=now(),
        status=MembershipStatus.ACTIVE, role=GroupRole.MEMBER,
    )  # fmt: skip
    session.add(membership)
    await session.flush()
    await session.refresh(membership)
    log.info("membership.added", group_id=group_id, member_user_id=user_id)
    return to_membership_out(membership)


async def join_by_code(session: AsyncSession, access: Access, code: str) -> MembershipOut:
    """Creates a PENDING membership and notifies every active group admin."""
    group = await repository.get_group_by_code(session, code)
    if group is None:
        raise AppError(ErrorCode.GROUP_NOT_FOUND, "Invalid group code")
    existing = await repository.get_membership(session, access.user.id, group.id)
    if existing is not None:
        raise AppError(
            ErrorCode.MEMBERSHIP_PENDING
            if existing.status == MembershipStatus.PENDING
            else ErrorCode.MEMBERSHIP_EXISTS
        )
    if await repository.count_members(session, group.id, active_only=True) >= group.total_members:
        raise AppError(ErrorCode.GROUP_FULL)
    membership = Membership(
        user_id=access.user.id, chit_group_id=group.id, join_date=now(),
        status=MembershipStatus.PENDING, role=GroupRole.MEMBER,
    )  # fmt: skip
    session.add(membership)
    for admin_id in await repository.active_admin_user_ids(session, group.id):
        await notifications.create_notification(
            session, admin_id, f"Join request from {access.user.name} for group {group.name}", "JOIN_REQUEST"
        )
    await session.flush()
    await session.refresh(membership)
    log.info("membership.join_requested", group_id=group.id)
    return to_membership_out(membership)


async def remove_member(session: AsyncSession, access: Access, group_id: int, user_id: int) -> None:
    await access.require_group_admin(group_id)
    membership = await repository.get_membership(session, user_id, group_id)
    if membership is None:
        raise AppError(ErrorCode.MEMBERSHIP_NOT_FOUND)
    await session.delete(membership)
    log.info("membership.removed", group_id=group_id, member_user_id=user_id)


async def list_members(session: AsyncSession, access: Access, group_id: int) -> list[MembershipOut]:
    """Group admins (and platform admins) also see PENDING/INACTIVE members."""
    await require_group(session, group_id)
    await access.require_group_member(group_id)
    active_only = not await access.is_group_admin(group_id)
    return [to_membership_out(m) for m in await repository.list_members(session, group_id, active_only)]


async def list_user_memberships(session: AsyncSession, access: Access, user_id: int) -> list[MembershipOut]:
    access.require_self_or_platform_admin(user_id)
    return [to_membership_out(m) for m in await repository.list_user_memberships(session, user_id)]


async def set_member_status(
    session: AsyncSession, access: Access, group_id: int, user_id: int, status: MembershipStatus
) -> MembershipOut:
    await access.require_group_admin(group_id)
    membership = await repository.get_membership(session, user_id, group_id)
    if membership is None:
        raise AppError(ErrorCode.MEMBERSHIP_NOT_FOUND)
    if (
        status == MembershipStatus.ACTIVE
        and membership.status != MembershipStatus.ACTIVE
        and await repository.count_members(session, group_id, active_only=True)
        >= membership.group.total_members
    ):
        raise AppError(ErrorCode.GROUP_FULL)
    membership.status = status
    await session.flush()
    log.info("membership.status_changed", group_id=group_id, member_user_id=user_id, status=status.value)
    return to_membership_out(membership)


async def visible_group_ids(session: AsyncSession, access: Access) -> Sequence[int] | None:
    """None = all groups (platform admin)."""
    if access.is_platform_admin:
        return None
    groups = await repository.list_groups(session, access.user.id, None, None)
    return [g.id for g in groups]
