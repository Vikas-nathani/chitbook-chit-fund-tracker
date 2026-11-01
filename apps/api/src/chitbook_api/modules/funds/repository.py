from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from chitbook_api.modules.funds.models import Fund


async def get(session: AsyncSession, fund_id: int) -> Fund | None:
    return await session.get(Fund, fund_id)


async def get_by_group(session: AsyncSession, group_id: int) -> Fund | None:
    return await session.scalar(select(Fund).where(Fund.chit_group_id == group_id))


async def list_for_groups(session: AsyncSession, group_ids: Sequence[int] | None) -> Sequence[Fund]:
    """group_ids=None means every fund."""
    stmt = select(Fund).order_by(Fund.id)
    if group_ids is not None:
        stmt = stmt.where(Fund.chit_group_id.in_(group_ids))
    return (await session.scalars(stmt)).all()
