"""Simple Chits: a chit run by one owner (the signed-in user) for a list of named members.

Rules:
- Each member pays `per_share_amount x shares` every month from their start month to the end.
- Months before a member's start month have no entry at all (not a zero).
- Payout escalation: when enabled, recording a payout adds `total_amount x escalation_percent / 100`
  to every *later* month of the taker. The exact bump is stored on the payout so deleting or
  replacing it reverses precisely.
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import ROUND_HALF_UP, Decimal

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from chitbook_api.core.errors import AppError, ErrorCode
from chitbook_api.core.time import YearMonth, now, today
from chitbook_api.modules.simple_chits import math, repository
from chitbook_api.modules.simple_chits.models import (
    SimpleChit,
    SimpleChitEntry,
    SimpleChitMember,
    SimpleChitPayout,
)
from chitbook_api.modules.simple_chits.schemas import (
    AddMember,
    MemberOut,
    MonthSummaryOut,
    PayoutOut,
    SavePayout,
    SimpleChitCreate,
    SimpleChitOut,
    SimpleChitSummaryOut,
    SimpleChitUpdate,
)
from chitbook_api.modules.users.models import User

log = structlog.get_logger("chitbook.simple_chits")

MAX_MONTHS = 120
MAX_MEMBERS = 100
MAX_NAME_LENGTH = 100
DEFAULT_COMMISSION_PERCENT = Decimal("5")
MAX_COMMISSION_PERCENT = Decimal("20")
DEFAULT_ESCALATION_PERCENT = Decimal("1")


# ---------------------------------------------------------------- validation helpers


def _invalid(message: str) -> AppError:
    return AppError(ErrorCode.CHIT_INVALID_INPUT, message)


def _require_name(value: str | None, label: str) -> str:
    trimmed = (value or "").strip()
    if not trimmed:
        raise _invalid(f"{label} is required")
    if len(trimmed) > MAX_NAME_LENGTH:
        raise _invalid(f"{label} must be at most {MAX_NAME_LENGTH} characters")
    return trimmed


def _require_positive(amount: Decimal | None, label: str) -> Decimal:
    if amount is None or not amount.is_finite() or amount <= 0:
        raise _invalid(f"{label} must be greater than 0")
    return math.money(amount)


def _require_commission(percent: Decimal) -> Decimal:
    if not percent.is_finite() or percent < 0 or percent > MAX_COMMISSION_PERCENT:
        raise _invalid(f"Commission must be between 0 and {MAX_COMMISSION_PERCENT}%")
    return percent


def _require_percent(percent: Decimal, label: str) -> Decimal:
    if not percent.is_finite() or percent < 0 or percent > 100:
        raise _invalid(f"{label} must be between 0 and 100")
    return percent


def _require_shares(shares: int | None) -> int:
    value = 1 if shares is None else shares
    if value < 1:
        raise _invalid("Shares must be at least 1")
    return value


def _parse_year_month(value: str) -> YearMonth:
    try:
        return YearMonth.parse(value)
    except ValueError as exc:
        raise _invalid("Start month must be in yyyy-MM format") from exc


def _resolve_start_index(chit_start: YearMonth, value: str | None, months: int, fallback: YearMonth) -> int:
    target = fallback if not value or not value.strip() else _parse_year_month(value)
    index = chit_start.months_until(target) + 1
    if not 1 <= index <= months:
        raise _invalid(f"Start month must fall within the chit's {months} months")
    return index


def _clamp(value: YearMonth, chit_start: YearMonth, months: int) -> YearMonth:
    last = chit_start.plus_months(months - 1)
    return min(max(value, chit_start), last)


def _require_month(chit: SimpleChit, month: int | None) -> int:
    if month is None or not 1 <= month <= chit.months:
        raise AppError(ErrorCode.CHIT_MONTH_OUT_OF_RANGE, f"Month must be between 1 and {chit.months}")
    return month


def _require_member(chit: SimpleChit, member_id: int | None) -> SimpleChitMember:
    for member in chit.members:
        if member.id == member_id:
            return member
    raise AppError(ErrorCode.CHIT_MEMBER_NOT_FOUND, f"Member {member_id} is not part of this chit")


# ---------------------------------------------------------------- domain helpers


def _add_member(chit: SimpleChit, name: str, shares: int, start_index: int, position: int) -> None:
    member = SimpleChitMember(name=name, position=position, shares=shares, start_month_index=start_index)
    amount = math.money(chit.per_share_amount * shares)
    member.entries = [
        SimpleChitEntry(month_index=m, amount=amount, paid=False) for m in range(start_index, chit.months + 1)
    ]
    chit.members.append(member)


def _adjust_later_months(member: SimpleChitMember, after_month: int, delta: Decimal) -> None:
    if delta == 0:
        return
    for entry in member.entries:
        if entry.month_index > after_month:
            entry.amount = math.money(entry.amount + delta)


async def _owned(session: AsyncSession, owner: User, chit_id: int) -> SimpleChit:
    chit = await repository.get_owned(session, chit_id, owner.id)
    if chit is None:
        raise AppError(ErrorCode.CHIT_NOT_FOUND)
    return chit


async def _saved(session: AsyncSession, chit: SimpleChit) -> SimpleChitOut:
    await session.flush()
    await session.refresh(chit, attribute_names=["created_at", "updated_at"])
    return to_out(chit)


# ---------------------------------------------------------------- use cases


async def create(session: AsyncSession, owner: User, data: SimpleChitCreate) -> SimpleChitOut:
    name = _require_name(data.name, "Chit name")
    total = _require_positive(data.total_amount, "Chit amount")
    months = data.months or 0
    if not 1 <= months <= MAX_MONTHS:
        raise _invalid(f"Months must be between 1 and {MAX_MONTHS}")
    start = (
        YearMonth.current()
        if not data.start_month or not data.start_month.strip()
        else _parse_year_month(data.start_month)
    )
    per_share = (
        _require_positive(data.per_share_amount, "Amount per share")
        if data.per_share_amount is not None
        else (total / months).quantize(math.CENT, rounding=ROUND_HALF_UP)
    )
    inputs = [m for m in (data.members or []) if m.name and m.name.strip()]
    if not 1 <= len(inputs) <= MAX_MEMBERS:
        raise _invalid(f"Add between 1 and {MAX_MEMBERS} members")

    chit = SimpleChit(
        owner_id=owner.id,
        name=name,
        total_amount=total,
        months=months,
        start_month=str(start),
        per_share_amount=per_share,
        commission_percent=(
            DEFAULT_COMMISSION_PERCENT
            if data.commission_percent is None
            else _require_commission(data.commission_percent)
        ),
        escalation_enabled=bool(data.escalation_enabled),
        escalation_percent=(
            DEFAULT_ESCALATION_PERCENT
            if data.escalation_percent is None
            else _require_percent(data.escalation_percent, "Escalation percent")
        ),
        members=[],
        payouts=[],
    )
    for position, member in enumerate(inputs):
        _add_member(
            chit,
            _require_name(member.name, "Member name"),
            _require_shares(member.shares),
            _resolve_start_index(start, member.start_month, months, start),
            position,
        )
    session.add(chit)
    out = await _saved(session, chit)
    log.info("simple_chit.created", chit_id=chit.id, months=months, members=len(inputs))
    return out


async def add_member(session: AsyncSession, owner: User, chit_id: int, data: AddMember) -> SimpleChitOut:
    chit = await _owned(session, owner, chit_id)
    name = _require_name(data.name, "Member name")
    shares = _require_shares(data.shares)
    start = math.start_of(chit)
    fallback = _clamp(YearMonth.current(), start, chit.months)
    start_index = _resolve_start_index(start, data.start_month, chit.months, fallback)
    position = max((m.position for m in chit.members), default=-1) + 1
    _add_member(chit, name, shares, start_index, position)
    out = await _saved(session, chit)
    log.info("simple_chit.member_added", chit_id=chit.id, start_month_index=start_index, shares=shares)
    return out


async def list_mine(session: AsyncSession, owner: User) -> list[SimpleChitSummaryOut]:
    current = YearMonth.current()
    return [to_summary(chit, current) for chit in await find_mine(session, owner)]


async def find_mine(session: AsyncSession, owner: User) -> Sequence[SimpleChit]:
    return await repository.list_owned(session, owner.id)


async def get(session: AsyncSession, owner: User, chit_id: int) -> SimpleChitOut:
    return to_out(await _owned(session, owner, chit_id))


async def update(session: AsyncSession, owner: User, chit_id: int, data: SimpleChitUpdate) -> SimpleChitOut:
    chit = await _owned(session, owner, chit_id)
    if data.total_amount is not None:
        chit.total_amount = _require_positive(data.total_amount, "Chit amount")
    if data.commission_percent is not None:
        chit.commission_percent = _require_commission(data.commission_percent)
    if data.per_share_amount is not None:
        chit.per_share_amount = _require_positive(data.per_share_amount, "Amount per share")
    if data.escalation_enabled is not None:
        chit.escalation_enabled = data.escalation_enabled
    if data.escalation_percent is not None:
        chit.escalation_percent = _require_percent(data.escalation_percent, "Escalation percent")

    for change in data.entries or []:
        member = _require_member(chit, change.member_id)
        month = _require_month(chit, change.month)
        entry = next((e for e in member.entries if e.month_index == month), None)
        if entry is None:
            entry = SimpleChitEntry(month_index=month, amount=Decimal("0"), paid=False)
            member.entries.append(entry)
        if change.amount is not None:
            if not change.amount.is_finite() or change.amount < 0:
                raise _invalid("Amounts cannot be negative")
            entry.amount = math.money(change.amount)
        if change.paid is not None and change.paid != entry.paid:
            entry.paid = change.paid
            entry.paid_at = now() if change.paid else None

    out = await _saved(session, chit)
    log.info("simple_chit.updated", chit_id=chit.id, entry_changes=len(data.entries or []))
    return out


async def save_payout(
    session: AsyncSession, owner: User, chit_id: int, month: int, data: SavePayout
) -> SimpleChitOut:
    chit = await _owned(session, owner, chit_id)
    month = _require_month(chit, month)
    member = _require_member(chit, data.member_id)
    amount = _require_positive(data.amount, "Payout amount")

    payout = next((p for p in chit.payouts if p.month_index == month), None)
    if payout is not None and payout.escalation_applied != 0:
        _adjust_later_months(payout.member, month, -payout.escalation_applied)  # undo the old bump first
    if payout is None:
        payout = SimpleChitPayout(month_index=month, escalation_applied=Decimal("0"))
        chit.payouts.append(payout)

    payout.member = member
    payout.amount = amount
    payout.paid_on = data.paid_on or today()

    bump = Decimal("0")
    if chit.escalation_enabled:
        bump = (chit.total_amount * chit.escalation_percent / 100).quantize(math.CENT, rounding=ROUND_HALF_UP)
        _adjust_later_months(member, month, bump)
    payout.escalation_applied = bump

    out = await _saved(session, chit)
    log.info(
        "simple_chit.payout_saved", chit_id=chit.id, month=month, member_id=member.id, escalation=str(bump)
    )
    return out


async def delete_payout(session: AsyncSession, owner: User, chit_id: int, month: int) -> SimpleChitOut:
    chit = await _owned(session, owner, chit_id)
    month = _require_month(chit, month)
    payout = next((p for p in chit.payouts if p.month_index == month), None)
    if payout is None:
        raise AppError(ErrorCode.CHIT_PAYOUT_NOT_FOUND, f"No payout recorded for month {month}")
    if payout.escalation_applied != 0:
        _adjust_later_months(payout.member, month, -payout.escalation_applied)
    chit.payouts.remove(payout)
    out = await _saved(session, chit)
    log.info("simple_chit.payout_deleted", chit_id=chit.id, month=month)
    return out


async def delete(session: AsyncSession, owner: User, chit_id: int) -> None:
    chit = await _owned(session, owner, chit_id)
    await session.delete(chit)  # members, entries and payouts cascade in the database
    log.info("simple_chit.deleted", chit_id=chit_id)


# ---------------------------------------------------------------- mapping


def to_out(chit: SimpleChit) -> SimpleChitOut:
    start = math.start_of(chit)
    members = []
    for member in chit.members:
        amounts: list[Decimal | None] = [None] * chit.months
        paid = [False] * chit.months
        for entry in member.entries:
            if 1 <= entry.month_index <= chit.months:
                amounts[entry.month_index - 1] = entry.amount
                paid[entry.month_index - 1] = entry.paid
        members.append(
            MemberOut(
                id=member.id,
                name=member.name,
                shares=member.shares,
                start_month=str(start.plus_months(member.start_month_index - 1)),
                amounts=amounts,
                paid=paid,
            )
        )
    payouts = [
        PayoutOut(month=p.month_index, member_id=p.member.id, member_name=p.member.name, amount=p.amount,
                  paid_on=p.paid_on)
        for p in chit.payouts
    ]  # fmt: skip
    summaries = [
        MonthSummaryOut(
            month=m.month, calendar_month=str(m.calendar_month), due=m.due, collected=m.collected,
            pending=m.pending, payout=m.payout, pnl=m.pnl, is_due=m.is_due,
        )
        for m in math.months(chit, YearMonth.current())
    ]  # fmt: skip
    return SimpleChitOut(
        id=chit.id,
        name=chit.name,
        total_amount=chit.total_amount,
        months=chit.months,
        start_month=chit.start_month,
        commission_percent=chit.commission_percent,
        per_share_amount=chit.per_share_amount,
        escalation_enabled=chit.escalation_enabled,
        escalation_percent=chit.escalation_percent,
        members=members,
        payouts=payouts,
        month_summaries=summaries,
        created_at=chit.created_at,
        updated_at=chit.updated_at,
    )


def to_summary(chit: SimpleChit, current: YearMonth) -> SimpleChitSummaryOut:
    s = math.summary(chit, current)
    return SimpleChitSummaryOut(
        id=chit.id,
        name=chit.name,
        total_amount=chit.total_amount,
        months=chit.months,
        start_month=chit.start_month,
        member_count=len(chit.members),
        commission_percent=chit.commission_percent,
        months_elapsed=s.months_elapsed,
        due_to_date=s.due_to_date,
        collected=s.collected,
        pending=s.pending,
        overdue=s.overdue,
        payouts_done=s.payouts_done,
        paid_out=s.paid_out,
        profit=s.profit,
        created_at=chit.created_at,
    )
