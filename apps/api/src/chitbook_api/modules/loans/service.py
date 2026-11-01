"""Loans given to members from a group's fund, with simple daily interest.

current_payable = principal + principal x annual_rate% x days_elapsed / 36500
(days counted in IST calendar days; PAID/CLOSED loans keep the value frozen at closing).
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from chitbook_api.core.deps import Access
from chitbook_api.core.errors import AppError, ErrorCode
from chitbook_api.core.time import now, to_app_tz, today
from chitbook_api.modules.groups.service import require_group
from chitbook_api.modules.loans import repository
from chitbook_api.modules.loans.models import LoanStatus, MemberLoan
from chitbook_api.modules.loans.schemas import LoanCreate, LoanOut, LoanSummaryOut

log = structlog.get_logger("chitbook.loans")

CLOSED_STATES = {LoanStatus.PAID, LoanStatus.CLOSED}


def current_payable(loan: MemberLoan) -> Decimal:
    if loan.status in CLOSED_STATES:
        return loan.current_payable
    days = (today() - to_app_tz(loan.start_date).date()).days
    if days <= 0:
        return loan.principal
    interest = loan.principal * loan.interest_rate * days / Decimal(36500)
    return (loan.principal + interest).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def to_out(loan: MemberLoan) -> LoanOut:
    g = loan.group
    return LoanOut(
        id=loan.id,
        principal=loan.principal,
        interest_rate=loan.interest_rate,
        tenure_months=loan.tenure_months,
        current_payable=current_payable(loan),
        start_date=loan.start_date,
        end_date=loan.end_date,
        status=loan.status,
        chit_group_id=g.id,
        chit_group_name=g.name,
        chit_group_code=g.group_code,
        user_id=loan.user_id,
        user_name=loan.user.name,
        created_at=loan.created_at,
        updated_at=loan.updated_at,
    )


def to_summary(loan: MemberLoan) -> LoanSummaryOut:
    days_remaining = None
    if loan.end_date is not None:
        days_remaining = max((to_app_tz(loan.end_date).date() - today()).days, 0)
    g = loan.group
    return LoanSummaryOut(
        loan_id=loan.id, chit_group_id=g.id, chit_group_name=g.name, chit_group_code=g.group_code,
        principal=loan.principal, current_payable=current_payable(loan), status=loan.status,
        days_remaining=days_remaining,
    )  # fmt: skip


async def create(session: AsyncSession, access: Access, data: LoanCreate) -> LoanOut:
    await require_group(session, data.chit_group_id)
    await access.require_group_admin(data.chit_group_id)
    if await access.active_membership(data.chit_group_id, data.user_id) is None:
        raise AppError(ErrorCode.NOT_GROUP_MEMBER, "Loans can only be given to active members of this group")
    loan = MemberLoan(
        user_id=data.user_id,
        chit_group_id=data.chit_group_id,
        principal=data.principal,
        interest_rate=data.interest_rate,
        tenure_months=data.tenure_months,
        current_payable=data.principal,
        start_date=data.start_date or now(),
        end_date=data.end_date,
        status=LoanStatus.ACTIVE,
    )
    session.add(loan)
    await session.flush()
    await session.refresh(loan)
    log.info("loan.created", loan_id=loan.id, group_id=data.chit_group_id, borrower_user_id=data.user_id)
    return to_out(loan)


async def set_status(session: AsyncSession, access: Access, loan_id: int, status: LoanStatus) -> LoanOut:
    loan = await repository.get(session, loan_id)
    if loan is None:
        raise AppError(ErrorCode.LOAN_NOT_FOUND)
    await access.require_group_admin(loan.chit_group_id)
    if status in CLOSED_STATES and loan.status not in CLOSED_STATES:
        loan.current_payable = current_payable(loan)  # freeze the amount at closing time
    loan.status = status
    await session.flush()
    await session.refresh(loan)
    log.info("loan.status_changed", loan_id=loan_id, status=status.value)
    return to_out(loan)


async def list_for_group(session: AsyncSession, access: Access, group_id: int) -> list[LoanOut]:
    await access.require_group_admin(group_id)
    return [to_out(loan) for loan in await repository.list_for_group(session, group_id)]


async def list_for_user(session: AsyncSession, access: Access, user_id: int) -> list[LoanSummaryOut]:
    access.require_self_or_platform_admin(user_id)
    return [to_summary(loan) for loan in await repository.list_for_user(session, user_id)]


async def latest_for_member(session: AsyncSession, access: Access, group_id: int, user_id: int) -> MemberLoan:
    await access.require_self_or_group_admin(user_id, group_id)
    loan = await repository.latest_for_member(session, user_id, group_id)
    if loan is None:
        raise AppError(ErrorCode.LOAN_NOT_FOUND)
    return loan
