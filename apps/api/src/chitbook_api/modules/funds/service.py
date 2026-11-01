"""The pooled fund of each chit group. Members can read it; group admins can change it."""

from __future__ import annotations

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from chitbook_api.core.deps import Access
from chitbook_api.core.errors import AppError, ErrorCode
from chitbook_api.modules.funds import repository
from chitbook_api.modules.funds.models import Fund
from chitbook_api.modules.funds.schemas import FundOut, FundUpdate
from chitbook_api.modules.groups.service import visible_group_ids

log = structlog.get_logger("chitbook.funds")


def to_out(f: Fund) -> FundOut:
    return FundOut(
        id=f.id, name=f.name, total_amount=f.total_amount, cycle_period=f.cycle_period,
        interest_rate=f.interest_rate, chit_group_id=f.chit_group_id, chit_group_name=f.group.name,
        created_at=f.created_at, updated_at=f.updated_at,
    )  # fmt: skip


async def _require(session: AsyncSession, fund_id: int) -> Fund:
    fund = await repository.get(session, fund_id)
    if fund is None:
        raise AppError(ErrorCode.FUND_NOT_FOUND)
    return fund


async def list_visible(session: AsyncSession, access: Access) -> list[FundOut]:
    group_ids = await visible_group_ids(session, access)
    return [to_out(f) for f in await repository.list_for_groups(session, group_ids)]


async def get(session: AsyncSession, access: Access, fund_id: int) -> FundOut:
    fund = await _require(session, fund_id)
    await access.require_group_member(fund.chit_group_id)
    return to_out(fund)


async def get_by_group(session: AsyncSession, access: Access, group_id: int) -> FundOut:
    await access.require_group_member(group_id)
    fund = await repository.get_by_group(session, group_id)
    if fund is None:
        raise AppError(ErrorCode.FUND_NOT_FOUND)
    return to_out(fund)


async def update(session: AsyncSession, access: Access, fund_id: int, data: FundUpdate) -> FundOut:
    fund = await _require(session, fund_id)
    await access.require_group_admin(fund.chit_group_id)
    if data.total_amount is not None:
        fund.total_amount = data.total_amount
    if data.interest_rate is not None:
        fund.interest_rate = data.interest_rate
    await session.flush()
    await session.refresh(fund)
    log.info("fund.updated", fund_id=fund_id, group_id=fund.chit_group_id)
    return to_out(fund)
