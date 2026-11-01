from __future__ import annotations

from fastapi import APIRouter, status

from chitbook_api.core.deps import CurrentUser, SessionDep
from chitbook_api.core.errors import AUTHED, ErrorCode, errors
from chitbook_api.modules.simple_chits import service, stats
from chitbook_api.modules.simple_chits.schemas import (
    AddMember,
    SavePayout,
    SimpleChitCreate,
    SimpleChitOut,
    SimpleChitStats,
    SimpleChitSummaryOut,
    SimpleChitUpdate,
)

router = APIRouter(prefix="/simple-chits", tags=["simple-chits"])


@router.get(
    "",
    response_model=list[SimpleChitSummaryOut],
    summary="List my chits with totals",
    responses=errors(*AUTHED),
)
async def list_chits(session: SessionDep, user: CurrentUser) -> object:
    return await service.list_mine(session, user)


@router.get(
    "/stats",
    response_model=SimpleChitStats,
    summary="Totals, monthly series and pending dues",
    responses=errors(*AUTHED),
)
async def get_stats(session: SessionDep, user: CurrentUser) -> object:
    return await stats.for_owner(session, user)


@router.post(
    "",
    response_model=SimpleChitOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a chit",
    responses=errors(*AUTHED, ErrorCode.VALIDATION_ERROR, ErrorCode.CHIT_INVALID_INPUT),
)
async def create_chit(body: SimpleChitCreate, session: SessionDep, user: CurrentUser) -> object:
    return await service.create(session, user, body)


@router.get(
    "/{chit_id}",
    response_model=SimpleChitOut,
    summary="Get one chit with its full grid",
    responses=errors(*AUTHED, ErrorCode.VALIDATION_ERROR, ErrorCode.CHIT_NOT_FOUND),
)
async def get_chit(chit_id: int, session: SessionDep, user: CurrentUser) -> object:
    return await service.get(session, user, chit_id)


@router.patch(
    "/{chit_id}",
    response_model=SimpleChitOut,
    summary="Update settings and/or grid cells",
    responses=errors(
        *AUTHED,
        ErrorCode.VALIDATION_ERROR,
        ErrorCode.CHIT_NOT_FOUND,
        ErrorCode.CHIT_INVALID_INPUT,
        ErrorCode.CHIT_MEMBER_NOT_FOUND,
        ErrorCode.CHIT_MONTH_OUT_OF_RANGE,
    ),
)
async def update_chit(chit_id: int, body: SimpleChitUpdate, session: SessionDep, user: CurrentUser) -> object:
    return await service.update(session, user, chit_id, body)


@router.delete(
    "/{chit_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a chit",
    responses=errors(*AUTHED, ErrorCode.VALIDATION_ERROR, ErrorCode.CHIT_NOT_FOUND),
)
async def delete_chit(chit_id: int, session: SessionDep, user: CurrentUser) -> None:
    await service.delete(session, user, chit_id)


@router.post(
    "/{chit_id}/members",
    response_model=SimpleChitOut,
    summary="Add a member (late joiners allowed)",
    responses=errors(
        *AUTHED, ErrorCode.VALIDATION_ERROR, ErrorCode.CHIT_NOT_FOUND, ErrorCode.CHIT_INVALID_INPUT
    ),
)
async def add_member(chit_id: int, body: AddMember, session: SessionDep, user: CurrentUser) -> object:
    return await service.add_member(session, user, chit_id, body)


@router.put(
    "/{chit_id}/payouts/{month}",
    response_model=SimpleChitOut,
    summary="Record or replace a payout",
    responses=errors(
        *AUTHED,
        ErrorCode.VALIDATION_ERROR,
        ErrorCode.CHIT_NOT_FOUND,
        ErrorCode.CHIT_MONTH_OUT_OF_RANGE,
        ErrorCode.CHIT_MEMBER_NOT_FOUND,
        ErrorCode.CHIT_INVALID_INPUT,
    ),
)
async def save_payout(
    chit_id: int, month: int, body: SavePayout, session: SessionDep, user: CurrentUser
) -> object:
    return await service.save_payout(session, user, chit_id, month, body)


@router.delete(
    "/{chit_id}/payouts/{month}",
    response_model=SimpleChitOut,
    summary="Delete a payout",
    responses=errors(
        *AUTHED,
        ErrorCode.VALIDATION_ERROR,
        ErrorCode.CHIT_NOT_FOUND,
        ErrorCode.CHIT_MONTH_OUT_OF_RANGE,
        ErrorCode.CHIT_PAYOUT_NOT_FOUND,
    ),
)
async def delete_payout(chit_id: int, month: int, session: SessionDep, user: CurrentUser) -> object:
    return await service.delete_payout(session, user, chit_id, month)
