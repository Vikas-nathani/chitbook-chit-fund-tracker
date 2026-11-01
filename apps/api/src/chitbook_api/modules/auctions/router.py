from __future__ import annotations

from fastapi import APIRouter, status

from chitbook_api.core.deps import AccessDep, SessionDep
from chitbook_api.core.errors import AUTHED, ErrorCode, errors
from chitbook_api.modules.auctions import service
from chitbook_api.modules.auctions.schemas import AuctionCreate, AuctionOut

router = APIRouter(prefix="/auctions", tags=["auctions"])


@router.post(
    "",
    response_model=AuctionOut,
    status_code=status.HTTP_201_CREATED,
    summary="Record an auction",
    responses=errors(
        *AUTHED,
        ErrorCode.VALIDATION_ERROR,
        ErrorCode.GROUP_NOT_FOUND,
        ErrorCode.NOT_GROUP_MEMBER,
        ErrorCode.NOT_GROUP_ADMIN,
        ErrorCode.AUCTION_EXISTS,
    ),
)
async def create_auction(body: AuctionCreate, session: SessionDep, access: AccessDep) -> object:
    return await service.create(session, access, body)


@router.get(
    "/group/{group_id}",
    response_model=list[AuctionOut],
    summary="A group's auctions",
    responses=errors(*AUTHED, ErrorCode.VALIDATION_ERROR, ErrorCode.NOT_GROUP_MEMBER),
)
async def group_auctions(group_id: int, session: SessionDep, access: AccessDep) -> object:
    return await service.list_for_group(session, access, group_id)


@router.get(
    "/winner/{user_id}",
    response_model=list[AuctionOut],
    summary="Auctions a user has won",
    responses=errors(*AUTHED, ErrorCode.VALIDATION_ERROR, ErrorCode.FORBIDDEN),
)
async def won_auctions(user_id: int, session: SessionDep, access: AccessDep) -> object:
    return await service.list_won_by(session, access, user_id)


@router.get(
    "/{auction_id}",
    response_model=AuctionOut,
    summary="Get an auction",
    responses=errors(
        *AUTHED, ErrorCode.VALIDATION_ERROR, ErrorCode.AUCTION_NOT_FOUND, ErrorCode.NOT_GROUP_MEMBER
    ),
)
async def get_auction(auction_id: int, session: SessionDep, access: AccessDep) -> object:
    return await service.get(session, access, auction_id)


@router.delete(
    "/{auction_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an auction",
    responses=errors(
        *AUTHED,
        ErrorCode.VALIDATION_ERROR,
        ErrorCode.AUCTION_NOT_FOUND,
        ErrorCode.NOT_GROUP_MEMBER,
        ErrorCode.NOT_GROUP_ADMIN,
    ),
)
async def delete_auction(auction_id: int, session: SessionDep, access: AccessDep) -> None:
    await service.delete(session, access, auction_id)
