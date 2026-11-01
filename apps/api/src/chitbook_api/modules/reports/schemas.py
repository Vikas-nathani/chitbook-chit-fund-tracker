from __future__ import annotations

from datetime import date

from chitbook_api.core.schemas import ApiModel, Money
from chitbook_api.modules.payments.schemas import PaymentOut


class AuditReport(ApiModel):
    group_id: int
    group_name: str
    unverified_payments_count: int
    total_unverified_amount: Money
    recent_unverified_payments: list[PaymentOut]


class GroupSummary(ApiModel):
    chit_group_id: int
    chit_group_name: str
    chit_group_code: str
    total_members: int
    monthly_contribution_amount: Money
    total_contributions_collected: Money
    total_loans_outstanding: Money
    fund_balance_approx: Money
    as_of_date: date


class MemberGroupSummary(ApiModel):
    user_id: int
    user_name: str
    chit_group_id: int
    chit_group_name: str
    chit_group_code: str
    total_contributions_paid: Money
    current_loan_payable: Money | None
    estimated_profit_share: Money | None
    as_of_date: date
