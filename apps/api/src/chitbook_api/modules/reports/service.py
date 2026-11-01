"""Financial reports for chit groups, calculated live from payments, loans and funds.

- total_contributions_collected = sum of COMPLETED payments dated up to the end of today (IST)
- total_loans_outstanding       = sum of current_payable over the group's loans
- fund_balance_approx           = the fund's total_amount (or contributions - loans if no fund)
- estimated_profit_share        = (fund_balance - contributions + loans) / active member count
"""

from __future__ import annotations

from datetime import datetime, time
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from chitbook_api.core.config import get_settings
from chitbook_api.core.deps import Access
from chitbook_api.core.time import today
from chitbook_api.modules.funds import repository as funds_repo
from chitbook_api.modules.groups import repository as groups_repo
from chitbook_api.modules.groups.models import ChitGroup
from chitbook_api.modules.groups.service import require_group
from chitbook_api.modules.loans import repository as loans_repo
from chitbook_api.modules.loans.service import current_payable
from chitbook_api.modules.payments import repository as payments_repo
from chitbook_api.modules.payments.service import to_out as payment_out
from chitbook_api.modules.reports.schemas import AuditReport, GroupSummary, MemberGroupSummary

RECENT_UNVERIFIED_LIMIT = 10
CENT = Decimal("0.01")


def _end_of_today() -> datetime:
    return datetime.combine(today(), time(23, 59, 59), tzinfo=get_settings().zone)


async def audit(session: AsyncSession, access: Access, group_id: int) -> AuditReport:
    group = await require_group(session, group_id)
    await access.require_group_admin(group_id)
    count, total = await payments_repo.unverified_totals(session, group_id)
    recent = await payments_repo.unverified_for_group(session, group_id, RECENT_UNVERIFIED_LIMIT)
    return AuditReport(
        group_id=group.id,
        group_name=group.name,
        unverified_payments_count=count,
        total_unverified_amount=total,
        recent_unverified_payments=[payment_out(p) for p in recent],
    )


async def _group_summary(session: AsyncSession, group: ChitGroup) -> GroupSummary:
    contributions = await payments_repo.sum_completed(session, group.id, _end_of_today())
    loans = sum(
        (current_payable(loan) for loan in await loans_repo.list_for_group(session, group.id)), Decimal("0")
    )
    fund = await funds_repo.get_by_group(session, group.id)
    return GroupSummary(
        chit_group_id=group.id,
        chit_group_name=group.name,
        chit_group_code=group.group_code,
        total_members=await groups_repo.count_members(session, group.id, active_only=True),
        monthly_contribution_amount=group.monthly_amount,
        total_contributions_collected=contributions,
        total_loans_outstanding=loans,
        fund_balance_approx=fund.total_amount if fund is not None else contributions - loans,
        as_of_date=today(),
    )


async def group_summary(session: AsyncSession, access: Access, group_id: int) -> GroupSummary:
    group = await require_group(session, group_id)
    await access.require_group_member(group_id)
    return await _group_summary(session, group)


async def member_summaries(session: AsyncSession, access: Access, user_id: int) -> list[MemberGroupSummary]:
    access.require_self_or_platform_admin(user_id)
    result: list[MemberGroupSummary] = []
    for membership in await groups_repo.list_user_memberships(session, user_id):
        if membership.status != "ACTIVE":
            continue
        group = membership.group
        summary = await _group_summary(session, group)
        contributions = await payments_repo.sum_completed(session, group.id, _end_of_today(), user_id)
        loan = await loans_repo.latest_for_member(session, user_id, group.id)
        pool = (
            summary.fund_balance_approx
            - summary.total_contributions_collected
            + summary.total_loans_outstanding
        )
        share = (
            (pool / summary.total_members).quantize(CENT, ROUND_HALF_UP) if summary.total_members else None
        )
        result.append(
            MemberGroupSummary(
                user_id=user_id,
                user_name=membership.user.name,
                chit_group_id=group.id,
                chit_group_name=group.name,
                chit_group_code=group.group_code,
                total_contributions_paid=contributions,
                current_loan_payable=current_payable(loan) if loan is not None else None,
                estimated_profit_share=share,
                as_of_date=today(),
            )
        )
    return result
