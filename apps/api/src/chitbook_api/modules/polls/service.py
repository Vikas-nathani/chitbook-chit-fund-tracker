"""Group polls: any active member can create a poll and vote once per poll."""

from __future__ import annotations

from collections.abc import Sequence

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from chitbook_api.core.deps import Access
from chitbook_api.core.errors import AppError, ErrorCode
from chitbook_api.core.time import now
from chitbook_api.modules.groups.service import require_group
from chitbook_api.modules.polls import repository
from chitbook_api.modules.polls.models import Poll, PollOption, PollStatus, PollVote
from chitbook_api.modules.polls.schemas import PollCreate, PollOptionOut, PollOut, VoteRequest

log = structlog.get_logger("chitbook.polls")


async def _to_out(session: AsyncSession, polls: Sequence[Poll], user_id: int) -> list[PollOut]:
    ids = [p.id for p in polls]
    counts = await repository.vote_counts(session, ids)
    mine = await repository.my_votes(session, ids, user_id)
    return [
        PollOut(
            id=p.id,
            group_id=p.chit_group_id,
            group_name=p.group.name,
            creator_id=p.created_by_id,
            creator_name=p.creator.name,
            question=p.question,
            status=_effective_status(p),
            expires_at=p.expires_at,
            created_at=p.created_at,
            options=[
                PollOptionOut(id=o.id, option_text=o.option_text, vote_count=counts.get(o.id, 0))
                for o in p.options
            ],
            my_vote_option_id=mine.get(p.id),
        )
        for p in polls
    ]


def _effective_status(poll: Poll) -> PollStatus:
    if poll.status == PollStatus.OPEN and poll.expires_at is not None and poll.expires_at <= now():
        return PollStatus.CLOSED
    return poll.status


async def _require(session: AsyncSession, poll_id: int) -> Poll:
    poll = await repository.get(session, poll_id)
    if poll is None:
        raise AppError(ErrorCode.POLL_NOT_FOUND)
    return poll


async def create(session: AsyncSession, access: Access, data: PollCreate) -> PollOut:
    await require_group(session, data.group_id)
    await access.require_group_member(data.group_id)
    poll = Poll(
        chit_group_id=data.group_id,
        created_by_id=access.user.id,
        question=data.question.strip(),
        status=PollStatus.OPEN,
        expires_at=data.expires_at,
        options=[PollOption(option_text=text.strip()) for text in data.options if text.strip()],
    )
    session.add(poll)
    await session.flush()
    await session.refresh(poll)
    log.info("poll.created", poll_id=poll.id, group_id=data.group_id)
    return (await _to_out(session, [poll], access.user.id))[0]


async def vote(session: AsyncSession, access: Access, data: VoteRequest) -> PollOut:
    poll = await _require(session, data.poll_id)
    await access.require_group_member(poll.chit_group_id)
    if _effective_status(poll) == PollStatus.CLOSED:
        raise AppError(ErrorCode.POLL_CLOSED)
    if not any(o.id == data.option_id for o in poll.options):
        raise AppError(ErrorCode.POLL_OPTION_INVALID)
    if await repository.get_vote(session, poll.id, access.user.id) is not None:
        raise AppError(ErrorCode.POLL_ALREADY_VOTED)
    session.add(PollVote(poll_id=poll.id, option_id=data.option_id, user_id=access.user.id))
    await session.flush()
    log.info("poll.voted", poll_id=poll.id)
    return (await _to_out(session, [poll], access.user.id))[0]


async def close(session: AsyncSession, access: Access, poll_id: int) -> PollOut:
    poll = await _require(session, poll_id)
    if poll.created_by_id != access.user.id:
        await access.require_group_admin(poll.chit_group_id)
    poll.status = PollStatus.CLOSED
    await session.flush()
    log.info("poll.closed", poll_id=poll_id)
    return (await _to_out(session, [poll], access.user.id))[0]


async def list_for_group(session: AsyncSession, access: Access, group_id: int) -> list[PollOut]:
    await access.require_group_member(group_id)
    return await _to_out(session, await repository.list_for_group(session, group_id), access.user.id)
