"""Pure month-by-month calculations for a simple chit (no database access).

Definitions for one month of a chit:
- due        = sum of every member's entry amount for that month
- collected  = sum of entries marked paid
- pending    = max(due - collected, 0)
- payout     = amount given to the month's taker (None if not recorded yet)
- pnl        = collected - payout (only when a payout exists)
- is_due     = the calendar month has started (<= current month)
- is_overdue = the calendar month is fully over (< current month)
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from chitbook_api.core.time import YearMonth
from chitbook_api.modules.simple_chits.models import SimpleChit, SimpleChitPayout

CENT = Decimal("0.01")
ZERO = Decimal("0.00")


def money(value: Decimal | float | int) -> Decimal:
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class MonthCalc:
    month: int  # 1-based month index within the chit
    calendar_month: YearMonth
    due: Decimal
    collected: Decimal
    pending: Decimal
    payout: Decimal | None
    pnl: Decimal | None
    is_due: bool
    is_overdue: bool


@dataclass(frozen=True)
class ChitSummary:
    months_elapsed: int
    due_to_date: Decimal
    collected: Decimal
    pending: Decimal
    overdue: Decimal
    payouts_done: int
    paid_out: Decimal
    profit: Decimal


def start_of(chit: SimpleChit) -> YearMonth:
    return YearMonth.parse(chit.start_month)


def months(chit: SimpleChit, current: YearMonth) -> list[MonthCalc]:
    start = start_of(chit)
    payouts: dict[int, SimpleChitPayout] = {}
    for p in chit.payouts:
        payouts.setdefault(p.month_index, p)

    due = [ZERO] * chit.months
    collected = [ZERO] * chit.months
    for member in chit.members:
        for entry in member.entries:
            i = entry.month_index - 1
            if not 0 <= i < chit.months:
                continue
            amount = money(entry.amount)
            due[i] += amount
            if entry.paid:
                collected[i] += amount

    result: list[MonthCalc] = []
    for i in range(chit.months):
        calendar = start.plus_months(i)
        payout = payouts.get(i + 1)
        payout_amount = money(payout.amount) if payout is not None else None
        result.append(
            MonthCalc(
                month=i + 1,
                calendar_month=calendar,
                due=due[i],
                collected=collected[i],
                pending=max(due[i] - collected[i], ZERO),
                payout=payout_amount,
                pnl=collected[i] - payout_amount if payout_amount is not None else None,
                is_due=calendar <= current,
                is_overdue=calendar < current,
            )
        )
    return result


def summary(chit: SimpleChit, current: YearMonth) -> ChitSummary:
    elapsed = payouts_done = 0
    due_to_date = collected = pending = overdue = paid_out = profit = ZERO
    for m in months(chit, current):
        collected += m.collected  # paid cells count even when paid ahead of their month
        if m.is_due:
            elapsed += 1
            due_to_date += m.due
            pending += m.pending
        if m.is_overdue:
            overdue += m.pending
        if m.payout is not None and m.pnl is not None:
            payouts_done += 1
            paid_out += m.payout
            profit += m.pnl
    return ChitSummary(elapsed, due_to_date, collected, pending, overdue, payouts_done, paid_out, profit)
