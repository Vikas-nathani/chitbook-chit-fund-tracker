from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import Field

from chitbook_api.core.schemas import ApiModel, AppDateTime, Money

# ---------- requests ----------


class MemberInput(ApiModel):
    name: str | None = None
    shares: int | None = Field(default=None, description="Slots this person holds (default 1)")
    start_month: str | None = Field(default=None, description="yyyy-MM the member joins (default chit start)")


class SimpleChitCreate(ApiModel):
    name: str | None = None
    total_amount: Decimal | None = None
    months: int | None = None
    start_month: str | None = Field(default=None, description="yyyy-MM (default current month)")
    per_share_amount: Decimal | None = Field(default=None, description="Default total_amount / months")
    members: list[MemberInput] | None = None
    commission_percent: Decimal | None = Field(default=None, description="0-20, default 5")
    escalation_enabled: bool | None = None
    escalation_percent: Decimal | None = Field(default=None, description="0-100, default 1")


class AddMember(ApiModel):
    name: str | None = None
    shares: int | None = None
    start_month: str | None = Field(default=None, description="yyyy-MM (default current month, clamped)")


class EntryChange(ApiModel):
    member_id: int | None = None
    month: int | None = None
    amount: Decimal | None = None
    paid: bool | None = None


class SimpleChitUpdate(ApiModel):
    total_amount: Decimal | None = None
    commission_percent: Decimal | None = None
    per_share_amount: Decimal | None = None
    escalation_enabled: bool | None = None
    escalation_percent: Decimal | None = None
    entries: list[EntryChange] | None = None


class SavePayout(ApiModel):
    member_id: int | None = None
    amount: Decimal | None = None
    paid_on: date | None = Field(default=None, description="Default today (IST)")


# ---------- responses ----------


class MemberOut(ApiModel):
    id: int
    name: str
    shares: int
    start_month: str
    amounts: list[Money | None] = Field(description="Index 0 = month 1; null before the member joined")
    paid: list[bool]


class PayoutOut(ApiModel):
    month: int
    member_id: int
    member_name: str
    amount: Money
    paid_on: date


class MonthSummaryOut(ApiModel):
    month: int
    calendar_month: str
    due: Money
    collected: Money
    pending: Money
    payout: Money | None
    pnl: Money | None
    is_due: bool


class SimpleChitOut(ApiModel):
    id: int
    name: str
    total_amount: Money
    months: int
    start_month: str
    commission_percent: Money
    per_share_amount: Money
    escalation_enabled: bool
    escalation_percent: Money
    members: list[MemberOut]
    payouts: list[PayoutOut]
    month_summaries: list[MonthSummaryOut]
    created_at: AppDateTime
    updated_at: AppDateTime


class SimpleChitSummaryOut(ApiModel):
    id: int
    name: str
    total_amount: Money
    months: int
    start_month: str
    member_count: int
    commission_percent: Money
    months_elapsed: int
    due_to_date: Money
    collected: Money
    pending: Money
    overdue: Money
    payouts_done: int
    paid_out: Money
    profit: Money
    created_at: AppDateTime


class StatsTotals(ApiModel):
    chits: int
    due_to_date: Money
    collected: Money
    pending: Money
    overdue: Money
    paid_out: Money
    cash_in_hand: Money
    profit: Money
    expected_commission: Money
    collection_rate: float | None = Field(description="collected / due, 0-1; null when nothing is due")


class StatsMonthPoint(ApiModel):
    month: str
    due: Money
    collected: Money
    payout: Money
    pnl: Money
    cumulative_pnl: Money


class PendingDue(ApiModel):
    chit_id: int
    chit_name: str
    member_id: int
    member_name: str
    month: int
    calendar_month: str
    amount: Money
    overdue: bool
    days_overdue: int


class SimpleChitStats(ApiModel):
    totals: StatsTotals
    monthly: list[StatsMonthPoint]
    per_chit: list[SimpleChitSummaryOut]
    pending_dues: list[PendingDue]
