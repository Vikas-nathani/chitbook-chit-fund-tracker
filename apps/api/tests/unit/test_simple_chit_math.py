"""Month math on in-memory chits (no database)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from chitbook_api.core.time import YearMonth
from chitbook_api.modules.simple_chits import math
from chitbook_api.modules.simple_chits.models import (
    SimpleChit,
    SimpleChitEntry,
    SimpleChitMember,
    SimpleChitPayout,
)

D = Decimal


def chit_with(entries: list[tuple[int, str, bool]], payouts: dict[int, str] | None = None) -> SimpleChit:
    """3-month chit starting 2026-08 with one member; entries = (month, amount, paid)."""
    member = SimpleChitMember(
        name="A",
        position=0,
        shares=1,
        start_month_index=1,
        entries=[SimpleChitEntry(month_index=m, amount=D(a), paid=p) for m, a, p in entries],
    )
    chit = SimpleChit(name="T", months=3, start_month="2026-08", members=[member], payouts=[])
    for month, amount in (payouts or {}).items():
        chit.payouts.append(
            SimpleChitPayout(month_index=month, amount=D(amount), paid_on=date(2026, 8, 1), member=member)
        )
    return chit


def test_due_collected_pending_per_month() -> None:
    chit = chit_with([(1, "100", True), (2, "100", False), (3, "100", False)])
    months = math.months(chit, YearMonth(2026, 9))
    assert [m.due for m in months] == [D("100.00")] * 3
    assert [m.collected for m in months] == [D("100.00"), D("0.00"), D("0.00")]
    assert [m.pending for m in months] == [D("0.00"), D("100.00"), D("100.00")]
    assert [str(m.calendar_month) for m in months] == ["2026-08", "2026-09", "2026-10"]


def test_due_and_overdue_flags() -> None:
    months = math.months(chit_with([]), YearMonth(2026, 9))
    assert [m.is_due for m in months] == [True, True, False]
    assert [m.is_overdue for m in months] == [True, False, False]


def test_pnl_only_when_payout_exists() -> None:
    chit = chit_with([(1, "100", True), (2, "100", True)], payouts={1: "90"})
    months = math.months(chit, YearMonth(2026, 9))
    assert months[0].payout == D("90.00")
    assert months[0].pnl == D("10.00")
    assert months[1].payout is None and months[1].pnl is None


def test_summary_counts_paid_ahead_and_overdue() -> None:
    # month 3 paid early (before it is due) still counts as collected
    chit = chit_with([(1, "100", False), (2, "100", True), (3, "100", True)], payouts={2: "150"})
    s = math.summary(chit, YearMonth(2026, 9))
    assert s.months_elapsed == 2
    assert s.due_to_date == D("200.00")
    assert s.collected == D("200.00")
    assert s.pending == D("100.00")
    assert s.overdue == D("100.00")  # August is over and unpaid
    assert (s.payouts_done, s.paid_out, s.profit) == (1, D("150.00"), D("-50.00"))


def test_money_rounds_half_up() -> None:
    assert math.money(D("1.005")) == D("1.01")
    assert math.money(2) == D("2.00")
