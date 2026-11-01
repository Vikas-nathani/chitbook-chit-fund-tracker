from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from chitbook_api.modules.polls.models import Poll, PollVote


async def get(session: AsyncSession, poll_id: int) -> Poll | None:
    return await session.get(Poll, poll_id)


async def list_for_group(session: AsyncSession, group_id: int) -> Sequence[Poll]:
    stmt = select(Poll).where(Poll.chit_group_id == group_id).order_by(Poll.created_at.desc())
    return (await session.scalars(stmt)).all()


async def vote_counts(session: AsyncSession, poll_ids: Sequence[int]) -> dict[int, int]:
    """option_id -> number of votes."""
    if not poll_ids:
        return {}
    rows = await session.execute(
        select(PollVote.option_id, func.count())
        .where(PollVote.poll_id.in_(poll_ids))
        .group_by(PollVote.option_id)
    )
    return {option_id: int(count) for option_id, count in rows.all()}


async def my_votes(session: AsyncSession, poll_ids: Sequence[int], user_id: int) -> dict[int, int]:
    """poll_id -> option_id the user voted for."""
    if not poll_ids:
        return {}
    rows = await session.execute(
        select(PollVote.poll_id, PollVote.option_id).where(
            PollVote.poll_id.in_(poll_ids), PollVote.user_id == user_id
        )
    )
    return {row[0]: row[1] for row in rows.all()}  # poll_id -> option_id


async def get_vote(session: AsyncSession, poll_id: int, user_id: int) -> PollVote | None:
    return await session.scalar(
        select(PollVote).where(PollVote.poll_id == poll_id, PollVote.user_id == user_id)
    )
