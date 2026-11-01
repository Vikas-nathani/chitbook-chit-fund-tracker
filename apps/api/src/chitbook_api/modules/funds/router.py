from __future__ import annotations

from fastapi import APIRouter

from chitbook_api.core.deps import AccessDep, SessionDep
from chitbook_api.core.errors import AUTHED, ErrorCode, errors
from chitbook_api.modules.funds import service
from chitbook_api.modules.funds.schemas import FundOut, FundUpdate

router = APIRouter(prefix="/funds", tags=["funds"])


@router.get(
    "", response_model=list[FundOut], summary="Funds of the groups I belong to", responses=errors(*AUTHED)
)
async def list_funds(session: SessionDep, access: AccessDep) -> object:
    return await service.list_visible(session, access)


@router.get(
    "/group/{group_id}",
    response_model=FundOut,
    summary="A group's fund",
    responses=errors(
        *AUTHED, ErrorCode.VALIDATION_ERROR, ErrorCode.NOT_GROUP_MEMBER, ErrorCode.FUND_NOT_FOUND
    ),
)
async def get_group_fund(group_id: int, session: SessionDep, access: AccessDep) -> object:
    return await service.get_by_group(session, access, group_id)


@router.get(
    "/{fund_id}",
    response_model=FundOut,
    summary="Get a fund",
    responses=errors(
        *AUTHED, ErrorCode.VALIDATION_ERROR, ErrorCode.FUND_NOT_FOUND, ErrorCode.NOT_GROUP_MEMBER
    ),
)
async def get_fund(fund_id: int, session: SessionDep, access: AccessDep) -> object:
    return await service.get(session, access, fund_id)


@router.patch(
    "/{fund_id}",
    response_model=FundOut,
    summary="Update fund amount and/or interest rate",
    responses=errors(
        *AUTHED,
        ErrorCode.VALIDATION_ERROR,
        ErrorCode.FUND_NOT_FOUND,
        ErrorCode.NOT_GROUP_MEMBER,
        ErrorCode.NOT_GROUP_ADMIN,
    ),
)
async def update_fund(fund_id: int, body: FundUpdate, session: SessionDep, access: AccessDep) -> object:
    return await service.update(session, access, fund_id, body)
