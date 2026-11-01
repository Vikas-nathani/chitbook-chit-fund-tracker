"""Monthly contributions paid into a chit group, and their verification."""

from __future__ import annotations

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from chitbook_api.core.deps import Access
from chitbook_api.core.errors import AppError, ErrorCode
from chitbook_api.core.time import now
from chitbook_api.modules.groups.service import require_group
from chitbook_api.modules.payments import repository
from chitbook_api.modules.payments.models import Payment, PaymentStatus
from chitbook_api.modules.payments.schemas import PaymentCreate, PaymentOut
from chitbook_api.modules.users import repository as users_repo
from chitbook_api.modules.users.models import UserRole

log = structlog.get_logger("chitbook.payments")


def to_out(p: Payment) -> PaymentOut:
    return PaymentOut(
        id=p.id, month=p.month, amount_paid=p.amount_paid, payment_date=p.payment_date, mode=p.mode,
        status=p.status, user_id=p.user_id, user_name=p.user.name, chit_group_id=p.chit_group_id,
        chit_group_name=p.group.name, verified=p.verified, verified_by_user_id=p.verified_by_id,
        verified_by_user_name=p.verified_by.name if p.verified_by else None, verified_at=p.verified_at,
        created_at=p.created_at, updated_at=p.updated_at,
    )  # fmt: skip


async def _can_manage_payments(access: Access, group_id: int) -> bool:
    """Platform admin, any ACCOUNTANT, or an admin of this group."""
    return access.user.role == UserRole.ACCOUNTANT or await access.is_group_admin(group_id)


async def _require(session: AsyncSession, payment_id: int) -> Payment:
    payment = await repository.get(session, payment_id)
    if payment is None:
        raise AppError(ErrorCode.PAYMENT_NOT_FOUND)
    return payment


async def _reload(session: AsyncSession, payment: Payment) -> PaymentOut:
    await session.flush()
    await session.refresh(payment)
    return to_out(payment)


async def create(session: AsyncSession, access: Access, data: PaymentCreate) -> PaymentOut:
    if await users_repo.get_by_id(session, data.user_id) is None:
        raise AppError(ErrorCode.USER_NOT_FOUND)
    await require_group(session, data.chit_group_id)
    if await access.active_membership(data.chit_group_id, data.user_id) is None:
        raise AppError(ErrorCode.PAYMENT_MEMBER_INACTIVE)
    if data.user_id != access.user.id and not await _can_manage_payments(access, data.chit_group_id):
        raise AppError(ErrorCode.PAYMENT_NOT_ALLOWED)

    payment = Payment(
        user_id=data.user_id,
        chit_group_id=data.chit_group_id,
        month=data.month,
        amount_paid=data.amount_paid,
        payment_date=data.payment_date or now(),
        mode=data.mode.upper(),
        status=PaymentStatus.COMPLETED,
        verified=False,
    )
    session.add(payment)
    out = await _reload(session, payment)
    log.info(
        "payment.recorded", payment_id=payment.id, group_id=data.chit_group_id, payer_user_id=data.user_id
    )
    return out


async def verify(session: AsyncSession, access: Access, payment_id: int) -> PaymentOut:
    payment = await _require(session, payment_id)
    if not await _can_manage_payments(access, payment.chit_group_id):
        raise AppError(ErrorCode.PAYMENT_VERIFY_NOT_ALLOWED)
    payment.verified = True
    payment.verified_by_id = access.user.id
    payment.verified_at = now()
    payment.status = PaymentStatus.COMPLETED
    out = await _reload(session, payment)
    log.info("payment.verified", payment_id=payment_id)
    return out


async def set_status(
    session: AsyncSession, access: Access, payment_id: int, status: PaymentStatus
) -> PaymentOut:
    payment = await _require(session, payment_id)
    await access.require_group_admin(payment.chit_group_id)
    payment.status = status
    out = await _reload(session, payment)
    log.info("payment.status_changed", payment_id=payment_id, status=status.value)
    return out


async def list_for_group(session: AsyncSession, access: Access, group_id: int) -> list[PaymentOut]:
    await access.require_group_admin(group_id)
    return [to_out(p) for p in await repository.list_for_group(session, group_id)]


async def list_for_member(
    session: AsyncSession, access: Access, group_id: int, user_id: int
) -> list[PaymentOut]:
    await access.require_self_or_group_admin(user_id, group_id)
    return [to_out(p) for p in await repository.list_for_group(session, group_id, user_id)]
