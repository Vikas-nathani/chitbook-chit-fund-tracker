"""Monthly auctions of a chit group: who won the pot, for how much, and the commission."""

from __future__ import annotations

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from chitbook_api.core.deps import Access
from chitbook_api.core.errors import AppError, ErrorCode
from chitbook_api.core.time import now
from chitbook_api.modules.auctions import repository
from chitbook_api.modules.auctions.models import Auction
from chitbook_api.modules.auctions.schemas import AuctionCreate, AuctionOut
from chitbook_api.modules.groups.service import require_group

log = structlog.get_logger("chitbook.auctions")


def to_out(a: Auction) -> AuctionOut:
    return AuctionOut(
        id=a.id, month=a.month, winning_amount=a.winning_amount, commission=a.commission,
        auction_date=a.auction_date, remark=a.remark, winning_member_id=a.winning_member_id,
        winning_member_name=a.winner.name, chit_group_id=a.chit_group_id, chit_group_name=a.group.name,
        created_at=a.created_at, updated_at=a.updated_at,
    )  # fmt: skip


async def _require(session: AsyncSession, auction_id: int) -> Auction:
    auction = await repository.get(session, auction_id)
    if auction is None:
        raise AppError(ErrorCode.AUCTION_NOT_FOUND)
    return auction


async def create(session: AsyncSession, access: Access, data: AuctionCreate) -> AuctionOut:
    await require_group(session, data.chit_group_id)
    await access.require_group_admin(data.chit_group_id)
    if await access.active_membership(data.chit_group_id, data.winning_member_id) is None:
        raise AppError(ErrorCode.NOT_GROUP_MEMBER, "The winner must be an active member of this group")
    if await repository.get_for_month(session, data.chit_group_id, data.month) is not None:
        raise AppError(ErrorCode.AUCTION_EXISTS)
    auction = Auction(
        chit_group_id=data.chit_group_id,
        winning_member_id=data.winning_member_id,
        month=data.month,
        winning_amount=data.winning_amount,
        commission=data.commission,
        auction_date=data.auction_date or now(),
        remark=data.remark,
    )
    session.add(auction)
    await session.flush()
    await session.refresh(auction)
    log.info("auction.created", auction_id=auction.id, group_id=data.chit_group_id, month=data.month)
    return to_out(auction)


async def get(session: AsyncSession, access: Access, auction_id: int) -> AuctionOut:
    auction = await _require(session, auction_id)
    await access.require_group_member(auction.chit_group_id)
    return to_out(auction)


async def list_for_group(session: AsyncSession, access: Access, group_id: int) -> list[AuctionOut]:
    await access.require_group_member(group_id)
    return [to_out(a) for a in await repository.list_for_group(session, group_id)]


async def list_won_by(session: AsyncSession, access: Access, user_id: int) -> list[AuctionOut]:
    access.require_self_or_platform_admin(user_id)
    return [to_out(a) for a in await repository.list_won_by(session, user_id)]


async def delete(session: AsyncSession, access: Access, auction_id: int) -> None:
    auction = await _require(session, auction_id)
    await access.require_group_admin(auction.chit_group_id)
    await session.delete(auction)
    log.info("auction.deleted", auction_id=auction_id)
