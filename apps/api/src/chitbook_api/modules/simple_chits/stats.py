"""Owner-wide statistics across all of the signed-in user's simple chits (Insights screen)."""

from __future__ import annotations

from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from chitbook_api.core.time import YearMonth, today
from chitbook_api.modules.simple_chits import math, service
from chitbook_api.modules.simple_chits.schemas import (
    PendingDue,
    SimpleChitStats,
    SimpleChitSummaryOut,
    StatsMonthPoint,
    StatsTotals,
)
from chitbook_api.modules.users.models import User

MAX_SERIES_MONTHS = 18  # chart shows at most the last 18 months
FUTURE_MONTHS = 2  # ...and at most 2 months ahead of today
ZERO = math.ZERO


async def for_owner(session: AsyncSession, owner: User) -> SimpleChitStats:
    current = YearMonth.current()
    day = today()
    chits = await service.find_mine(session, owner)

    per_chit: list[SimpleChitSummaryOut] = []
    # month -> [due, collected, payout, pnl]
    monthly: dict[YearMonth, list[Decimal]] = defaultdict(lambda: [ZERO, ZERO, ZERO, ZERO])
    pending_dues: list[PendingDue] = []
    expected_commission = ZERO

    for chit in chits:
        per_chit.append(service.to_summary(chit, current))
        expected_commission += (chit.total_amount * chit.commission_percent / 100).quantize(
            math.CENT, rounding=ROUND_HALF_UP
        ) * chit.months
        for m in math.months(chit, current):
            point = monthly[m.calendar_month]
            point[0] += m.due
            point[1] += m.collected
            if m.payout is not None and m.pnl is not None:
                point[2] += m.payout
                point[3] += m.pnl

        start = math.start_of(chit)
        for member in chit.members:
            for entry in member.entries:
                calendar = start.plus_months(entry.month_index - 1)
                if entry.paid or entry.amount <= 0 or calendar > current:
                    continue
                overdue = calendar < current
                # Overdue counts from the first day of the following month
                days = (day - calendar.plus_months(1).first_day()).days if overdue else 0
                pending_dues.append(
                    PendingDue(
                        chit_id=chit.id,
                        chit_name=chit.name,
                        member_id=member.id,
                        member_name=member.name,
                        month=entry.month_index,
                        calendar_month=str(calendar),
                        amount=math.money(entry.amount),
                        overdue=overdue,
                        days_overdue=max(days, 0),
                    )
                )

    pending_dues.sort(key=lambda d: (d.calendar_month, d.chit_name, d.member_name))
    return SimpleChitStats(
        totals=_totals(per_chit, expected_commission),
        monthly=_series(monthly, current),
        per_chit=per_chit,
        pending_dues=pending_dues,
    )


def _totals(per_chit: list[SimpleChitSummaryOut], expected_commission: Decimal) -> StatsTotals:
    due = sum((c.due_to_date for c in per_chit), ZERO)
    collected = sum((c.collected for c in per_chit), ZERO)
    paid_out = sum((c.paid_out for c in per_chit), ZERO)
    rate = None if due == 0 else float((min(collected, due) / due).quantize(Decimal("0.0001"), ROUND_HALF_UP))
    return StatsTotals(
        chits=len(per_chit),
        due_to_date=due,
        collected=collected,
        pending=sum((c.pending for c in per_chit), ZERO),
        overdue=sum((c.overdue for c in per_chit), ZERO),
        paid_out=paid_out,
        cash_in_hand=collected - paid_out,
        profit=sum((c.profit for c in per_chit), ZERO),
        expected_commission=expected_commission,
        collection_rate=rate,
    )


def _series(monthly: dict[YearMonth, list[Decimal]], current: YearMonth) -> list[StatsMonthPoint]:
    if not monthly:
        return []
    first, last = min(monthly), max(monthly)
    end = min(last, current.plus_months(FUTURE_MONTHS))
    points: list[StatsMonthPoint] = []
    cumulative = ZERO
    ym = first
    while ym <= end:
        due, collected, payout, pnl = monthly.get(ym, [ZERO, ZERO, ZERO, ZERO])
        cumulative += pnl
        points.append(
            StatsMonthPoint(
                month=str(ym), due=due, collected=collected, payout=payout, pnl=pnl, cumulative_pnl=cumulative
            )
        )
        ym = ym.plus_months(1)
    # cumulative is computed over the full range first, so trimming keeps correct running totals
    return points[-MAX_SERIES_MONTHS:]
