from __future__ import annotations

from fastapi import APIRouter, status

from chitbook_api.core.deps import AccessDep, SessionDep
from chitbook_api.core.errors import AUTHED, ErrorCode, errors
from chitbook_api.modules.payments import service
from chitbook_api.modules.payments.schemas import PaymentCreate, PaymentOut, PaymentStatusUpdate

router = APIRouter(prefix="/payments", tags=["payments"])

GROUP_ADMIN = (ErrorCode.NOT_GROUP_MEMBER, ErrorCode.NOT_GROUP_ADMIN)


@router.post(
    "",
    response_model=PaymentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Record a payment",
    responses=errors(
        *AUTHED,
        ErrorCode.VALIDATION_ERROR,
        ErrorCode.GROUP_NOT_FOUND,
        ErrorCode.USER_NOT_FOUND,
        ErrorCode.PAYMENT_NOT_ALLOWED,
        ErrorCode.PAYMENT_MEMBER_INACTIVE,
    ),
)
async def create_payment(body: PaymentCreate, session: SessionDep, access: AccessDep) -> object:
    return await service.create(session, access, body)


@router.post(
    "/{payment_id}/verify",
    response_model=PaymentOut,
    summary="Mark a payment verified",
    responses=errors(
        *AUTHED, ErrorCode.VALIDATION_ERROR, ErrorCode.PAYMENT_NOT_FOUND, ErrorCode.PAYMENT_VERIFY_NOT_ALLOWED
    ),
)
async def verify_payment(payment_id: int, session: SessionDep, access: AccessDep) -> object:
    return await service.verify(session, access, payment_id)


@router.put(
    "/{payment_id}/status",
    response_model=PaymentOut,
    summary="Change a payment's status",
    responses=errors(*AUTHED, ErrorCode.VALIDATION_ERROR, ErrorCode.PAYMENT_NOT_FOUND, *GROUP_ADMIN),
)
async def set_payment_status(
    payment_id: int, body: PaymentStatusUpdate, session: SessionDep, access: AccessDep
) -> object:
    return await service.set_status(session, access, payment_id, body.status)


@router.get(
    "/group/{group_id}",
    response_model=list[PaymentOut],
    summary="All payments of a group",
    responses=errors(*AUTHED, ErrorCode.VALIDATION_ERROR, *GROUP_ADMIN),
)
async def group_payments(group_id: int, session: SessionDep, access: AccessDep) -> object:
    return await service.list_for_group(session, access, group_id)


@router.get(
    "/group/{group_id}/user/{user_id}",
    response_model=list[PaymentOut],
    summary="One member's payments in a group",
    responses=errors(*AUTHED, ErrorCode.VALIDATION_ERROR, *GROUP_ADMIN),
)
async def member_payments(group_id: int, user_id: int, session: SessionDep, access: AccessDep) -> object:
    return await service.list_for_member(session, access, group_id, user_id)
