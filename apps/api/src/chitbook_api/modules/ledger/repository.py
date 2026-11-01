from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from chitbook_api.modules.ledger.models import LedgerEntry


async def get(session: AsyncSession, entry_id: int) -> LedgerEntry | None:
    return await session.get(LedgerEntry, entry_id)


async def search(
    session: AsyncSession, group_id: int | None = None, user_id: int | None = None
) -> Sequence[LedgerEntry]:
    stmt = select(LedgerEntry).order_by(LedgerEntry.entry_date.desc(), LedgerEntry.id.desc())
    if group_id is not None:
        stmt = stmt.where(LedgerEntry.chit_group_id == group_id)
    if user_id is not None:
        stmt = stmt.where(LedgerEntry.user_id == user_id)
    return (await session.scalars(stmt)).all()
