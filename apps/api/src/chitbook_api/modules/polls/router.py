from __future__ import annotations

from fastapi import APIRouter, status

from chitbook_api.core.deps import AccessDep, SessionDep
from chitbook_api.core.errors import AUTHED, ErrorCode, errors
from chitbook_api.modules.polls import service
from chitbook_api.modules.polls.schemas import PollCreate, PollOut, VoteRequest

router = APIRouter(prefix="/polls", tags=["polls"])


@router.post(
    "",
    response_model=PollOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a poll in a group",
    responses=errors(
        *AUTHED, ErrorCode.VALIDATION_ERROR, ErrorCode.GROUP_NOT_FOUND, ErrorCode.NOT_GROUP_MEMBER
    ),
)
async def create_poll(body: PollCreate, session: SessionDep, access: AccessDep) -> object:
    return await service.create(session, access, body)


@router.post(
    "/vote",
    response_model=PollOut,
    summary="Vote once in a poll",
    responses=errors(
        *AUTHED,
        ErrorCode.VALIDATION_ERROR,
        ErrorCode.POLL_NOT_FOUND,
        ErrorCode.NOT_GROUP_MEMBER,
        ErrorCode.POLL_CLOSED,
        ErrorCode.POLL_OPTION_INVALID,
        ErrorCode.POLL_ALREADY_VOTED,
    ),
)
async def vote(body: VoteRequest, session: SessionDep, access: AccessDep) -> object:
    return await service.vote(session, access, body)


@router.put(
    "/{poll_id}/close",
    response_model=PollOut,
    summary="Close a poll (creator or group admin)",
    responses=errors(
        *AUTHED,
        ErrorCode.VALIDATION_ERROR,
        ErrorCode.POLL_NOT_FOUND,
        ErrorCode.NOT_GROUP_MEMBER,
        ErrorCode.NOT_GROUP_ADMIN,
    ),
)
async def close_poll(poll_id: int, session: SessionDep, access: AccessDep) -> object:
    return await service.close(session, access, poll_id)


@router.get(
    "/group/{group_id}",
    response_model=list[PollOut],
    summary="A group's polls with vote counts",
    responses=errors(*AUTHED, ErrorCode.VALIDATION_ERROR, ErrorCode.NOT_GROUP_MEMBER),
)
async def group_polls(group_id: int, session: SessionDep, access: AccessDep) -> object:
    return await service.list_for_group(session, access, group_id)
