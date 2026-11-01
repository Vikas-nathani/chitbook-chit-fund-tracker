from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from chitbook_api.modules.auctions.models import Auction


async def get(session: AsyncSession, auction_id: int) -> Auction | None:
    return await session.get(Auction, auction_id)


async def get_for_month(session: AsyncSession, group_id: int, month: str) -> Auction | None:
    return await session.scalar(
        select(Auction).where(Auction.chit_group_id == group_id, Auction.month == month)
    )


async def list_for_group(session: AsyncSession, group_id: int) -> Sequence[Auction]:
    stmt = select(Auction).where(Auction.chit_group_id == group_id).order_by(Auction.auction_date)
    return (await session.scalars(stmt)).all()


async def list_won_by(session: AsyncSession, user_id: int) -> Sequence[Auction]:
    stmt = select(Auction).where(Auction.winning_member_id == user_id).order_by(Auction.auction_date.desc())
    return (await session.scalars(stmt)).all()
