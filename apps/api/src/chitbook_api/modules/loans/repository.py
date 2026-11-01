from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from chitbook_api.modules.loans.models import MemberLoan


async def get(session: AsyncSession, loan_id: int) -> MemberLoan | None:
    return await session.get(MemberLoan, loan_id)


async def list_for_group(session: AsyncSession, group_id: int) -> Sequence[MemberLoan]:
    stmt = (
        select(MemberLoan).where(MemberLoan.chit_group_id == group_id).order_by(MemberLoan.start_date.desc())
    )
    return (await session.scalars(stmt)).all()


async def list_for_user(session: AsyncSession, user_id: int) -> Sequence[MemberLoan]:
    stmt = select(MemberLoan).where(MemberLoan.user_id == user_id).order_by(MemberLoan.start_date.desc())
    return (await session.scalars(stmt)).all()


async def latest_for_member(session: AsyncSession, user_id: int, group_id: int) -> MemberLoan | None:
    stmt = (
        select(MemberLoan)
        .where(MemberLoan.user_id == user_id, MemberLoan.chit_group_id == group_id)
        .order_by(MemberLoan.start_date.desc(), MemberLoan.id.desc())
        .limit(1)
    )
    return await session.scalar(stmt)
