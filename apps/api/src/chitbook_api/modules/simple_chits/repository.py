from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from chitbook_api.modules.simple_chits.models import SimpleChit


async def get_owned(session: AsyncSession, chit_id: int, owner_id: int) -> SimpleChit | None:
    """Loads the chit with members, entries and payouts (selectin) if `owner_id` owns it."""
    return await session.scalar(
        select(SimpleChit).where(SimpleChit.id == chit_id, SimpleChit.owner_id == owner_id)
    )


async def list_owned(session: AsyncSession, owner_id: int) -> Sequence[SimpleChit]:
    stmt = select(SimpleChit).where(SimpleChit.owner_id == owner_id).order_by(SimpleChit.created_at.desc())
    return (await session.scalars(stmt)).all()
