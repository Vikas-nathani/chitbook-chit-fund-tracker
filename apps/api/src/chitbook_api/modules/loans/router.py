from __future__ import annotations

from fastapi import APIRouter, status

from chitbook_api.core.deps import AccessDep, SessionDep
from chitbook_api.core.errors import AUTHED, ErrorCode, errors
from chitbook_api.modules.loans import service
from chitbook_api.modules.loans.schemas import (
    LoanCreate,
    LoanOut,
    LoanStatusUpdate,
    LoanSummaryOut,
    PayableOut,
)

router = APIRouter(prefix="/loans", tags=["loans"])

# A member's own loan: the caller is that member or the group's admin
MEMBER_LOAN_ERRORS = (
    ErrorCode.NOT_GROUP_MEMBER,
    ErrorCode.NOT_GROUP_ADMIN,
    ErrorCode.LOAN_NOT_FOUND,
)


@router.post(
    "",
    response_model=LoanOut,
    status_code=status.HTTP_201_CREATED,
    summary="Give a loan to a member",
    responses=errors(
        *AUTHED,
        ErrorCode.VALIDATION_ERROR,
        ErrorCode.GROUP_NOT_FOUND,
        ErrorCode.NOT_GROUP_MEMBER,
        ErrorCode.NOT_GROUP_ADMIN,
    ),
)
async def create_loan(body: LoanCreate, session: SessionDep, access: AccessDep) -> object:
    return await service.create(session, access, body)


@router.put(
    "/{loan_id}/status",
    response_model=LoanOut,
    summary="Change loan status (PAID/CLOSED freezes it)",
    responses=errors(
        *AUTHED,
        ErrorCode.VALIDATION_ERROR,
        ErrorCode.LOAN_NOT_FOUND,
        ErrorCode.NOT_GROUP_MEMBER,
        ErrorCode.NOT_GROUP_ADMIN,
    ),
)
async def set_loan_status(
    loan_id: int, body: LoanStatusUpdate, session: SessionDep, access: AccessDep
) -> object:
    return await service.set_status(session, access, loan_id, body.status)


@router.get(
    "/group/{group_id}",
    response_model=list[LoanOut],
    summary="All loans in a group",
    responses=errors(
        *AUTHED, ErrorCode.VALIDATION_ERROR, ErrorCode.NOT_GROUP_MEMBER, ErrorCode.NOT_GROUP_ADMIN
    ),
)
async def group_loans(group_id: int, session: SessionDep, access: AccessDep) -> object:
    return await service.list_for_group(session, access, group_id)


@router.get(
    "/user/{user_id}",
    response_model=list[LoanSummaryOut],
    summary="A user's loans across groups",
    responses=errors(*AUTHED, ErrorCode.VALIDATION_ERROR, ErrorCode.FORBIDDEN),
)
async def user_loans(user_id: int, session: SessionDep, access: AccessDep) -> object:
    return await service.list_for_user(session, access, user_id)


@router.get(
    "/group/{group_id}/user/{user_id}",
    response_model=LoanOut,
    summary="A member's latest loan in a group",
    responses=errors(*AUTHED, ErrorCode.VALIDATION_ERROR, *MEMBER_LOAN_ERRORS),
)
async def member_loan(group_id: int, user_id: int, session: SessionDep, access: AccessDep) -> object:
    return service.to_out(await service.latest_for_member(session, access, group_id, user_id))


@router.get(
    "/group/{group_id}/user/{user_id}/payable",
    response_model=PayableOut,
    summary="What a member owes on their latest loan today",
    responses=errors(*AUTHED, ErrorCode.VALIDATION_ERROR, *MEMBER_LOAN_ERRORS),
)
async def member_payable(group_id: int, user_id: int, session: SessionDep, access: AccessDep) -> PayableOut:
    loan = await service.latest_for_member(session, access, group_id, user_id)
    return PayableOut(loan_id=loan.id, current_payable=service.current_payable(loan))
