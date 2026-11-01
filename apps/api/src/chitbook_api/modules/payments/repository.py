from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from chitbook_api.modules.payments.models import Payment, PaymentStatus


async def get(session: AsyncSession, payment_id: int) -> Payment | None:
    return await session.get(Payment, payment_id)


async def list_for_group(
    session: AsyncSession, group_id: int, user_id: int | None = None
) -> Sequence[Payment]:
    stmt = select(Payment).where(Payment.chit_group_id == group_id).order_by(Payment.payment_date.desc())
    if user_id is not None:
        stmt = stmt.where(Payment.user_id == user_id)
    return (await session.scalars(stmt)).all()


async def unverified_for_group(session: AsyncSession, group_id: int, limit: int) -> Sequence[Payment]:
    stmt = (
        select(Payment)
        .where(Payment.chit_group_id == group_id, Payment.verified.is_(False))
        .order_by(Payment.created_at.desc())
        .limit(limit)
    )
    return (await session.scalars(stmt)).all()


async def unverified_totals(session: AsyncSession, group_id: int) -> tuple[int, Decimal]:
    row = (
        await session.execute(
            select(func.count(), func.coalesce(func.sum(Payment.amount_paid), 0)).where(
                Payment.chit_group_id == group_id, Payment.verified.is_(False)
            )
        )
    ).one()
    return int(row[0]), Decimal(row[1])


async def sum_completed(
    session: AsyncSession, group_id: int, up_to: datetime, user_id: int | None = None
) -> Decimal:
    stmt = select(func.coalesce(func.sum(Payment.amount_paid), 0)).where(
        Payment.chit_group_id == group_id,
        Payment.status == PaymentStatus.COMPLETED,
        Payment.payment_date <= up_to,
    )
    if user_id is not None:
        stmt = stmt.where(Payment.user_id == user_id)
    return Decimal(await session.scalar(stmt) or 0)
