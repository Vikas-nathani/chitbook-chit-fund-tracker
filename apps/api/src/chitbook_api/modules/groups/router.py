from __future__ import annotations

from fastapi import APIRouter, Query, status

from chitbook_api.core.deps import AccessDep, SessionDep
from chitbook_api.core.errors import AUTHED, ErrorCode, errors
from chitbook_api.modules.groups import service
from chitbook_api.modules.groups.models import GroupStatus
from chitbook_api.modules.groups.schemas import (
    AddMemberRequest,
    GroupCreate,
    GroupOut,
    GroupStatusUpdate,
    GroupUpdate,
    JoinRequest,
    MembershipOut,
    MembershipStatusUpdate,
)

router = APIRouter(prefix="/groups", tags=["groups"])

# Group admin routes: the group must exist, and the caller must be its active ADMIN
ADMIN_ONLY = (ErrorCode.GROUP_NOT_FOUND, ErrorCode.NOT_GROUP_MEMBER, ErrorCode.NOT_GROUP_ADMIN)


@router.post(
    "",
    response_model=GroupOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a chit group",
    responses=errors(*AUTHED, ErrorCode.VALIDATION_ERROR),
)
async def create_group(body: GroupCreate, session: SessionDep, access: AccessDep) -> object:
    return await service.create(session, access, body)


@router.get(
    "",
    response_model=list[GroupOut],
    summary="List my groups (search by name / filter by status)",
    responses=errors(*AUTHED, ErrorCode.VALIDATION_ERROR),
)
async def list_groups(
    session: SessionDep,
    access: AccessDep,
    name: str | None = Query(default=None, max_length=100),
    group_status: GroupStatus | None = Query(default=None, alias="status"),
) -> object:
    return await service.list_visible(session, access, name, group_status)


@router.post(
    "/join",
    response_model=MembershipOut,
    status_code=status.HTTP_201_CREATED,
    summary="Ask to join a group by its code",
    responses=errors(
        *AUTHED,
        ErrorCode.VALIDATION_ERROR,
        ErrorCode.GROUP_NOT_FOUND,
        ErrorCode.MEMBERSHIP_EXISTS,
        ErrorCode.MEMBERSHIP_PENDING,
        ErrorCode.GROUP_FULL,
    ),
)
async def join_group(body: JoinRequest, session: SessionDep, access: AccessDep) -> object:
    return await service.join_by_code(session, access, body.group_code)


@router.get(
    "/memberships/user/{user_id}",
    response_model=list[MembershipOut],
    summary="A user's memberships",
    responses=errors(*AUTHED, ErrorCode.VALIDATION_ERROR, ErrorCode.FORBIDDEN),
)
async def user_memberships(user_id: int, session: SessionDep, access: AccessDep) -> object:
    return await service.list_user_memberships(session, access, user_id)


@router.get(
    "/by-code/{group_code}",
    response_model=GroupOut,
    summary="Get a group by its code",
    responses=errors(
        *AUTHED, ErrorCode.VALIDATION_ERROR, ErrorCode.GROUP_NOT_FOUND, ErrorCode.NOT_GROUP_MEMBER
    ),
)
async def get_group_by_code(group_code: str, session: SessionDep, access: AccessDep) -> object:
    return await service.get_by_code(session, access, group_code)


@router.get(
    "/{group_id}",
    response_model=GroupOut,
    summary="Get a group",
    responses=errors(
        *AUTHED, ErrorCode.VALIDATION_ERROR, ErrorCode.GROUP_NOT_FOUND, ErrorCode.NOT_GROUP_MEMBER
    ),
)
async def get_group(group_id: int, session: SessionDep, access: AccessDep) -> object:
    return await service.get(session, access, group_id)


@router.patch(
    "/{group_id}",
    response_model=GroupOut,
    summary="Update group settings",
    responses=errors(*AUTHED, ErrorCode.VALIDATION_ERROR, *ADMIN_ONLY),
)
async def update_group(group_id: int, body: GroupUpdate, session: SessionDep, access: AccessDep) -> object:
    return await service.update(session, access, group_id, body)


@router.put(
    "/{group_id}/status",
    response_model=GroupOut,
    summary="Change group status",
    responses=errors(*AUTHED, ErrorCode.VALIDATION_ERROR, *ADMIN_ONLY),
)
async def set_group_status(
    group_id: int, body: GroupStatusUpdate, session: SessionDep, access: AccessDep
) -> object:
    return await service.set_status(session, access, group_id, body.status)


@router.delete(
    "/{group_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a group",
    responses=errors(*AUTHED, ErrorCode.VALIDATION_ERROR, *ADMIN_ONLY),
)
async def delete_group(group_id: int, session: SessionDep, access: AccessDep) -> None:
    await service.delete(session, access, group_id)


@router.get(
    "/{group_id}/members",
    response_model=list[MembershipOut],
    summary="List group members",
    responses=errors(
        *AUTHED, ErrorCode.VALIDATION_ERROR, ErrorCode.GROUP_NOT_FOUND, ErrorCode.NOT_GROUP_MEMBER
    ),
)
async def list_members(group_id: int, session: SessionDep, access: AccessDep) -> object:
    return await service.list_members(session, access, group_id)


@router.post(
    "/{group_id}/members",
    response_model=MembershipOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add a user to the group",
    responses=errors(
        *AUTHED,
        ErrorCode.VALIDATION_ERROR,
        *ADMIN_ONLY,
        ErrorCode.USER_NOT_FOUND,
        ErrorCode.MEMBERSHIP_EXISTS,
        ErrorCode.GROUP_FULL,
    ),
)
async def add_member(group_id: int, body: AddMemberRequest, session: SessionDep, access: AccessDep) -> object:
    return await service.add_member(session, access, group_id, body.user_id)


@router.put(
    "/{group_id}/members/{user_id}/status",
    response_model=MembershipOut,
    summary="Approve / suspend / deactivate a member",
    responses=errors(
        *AUTHED,
        ErrorCode.VALIDATION_ERROR,
        ErrorCode.NOT_GROUP_MEMBER,
        ErrorCode.NOT_GROUP_ADMIN,
        ErrorCode.MEMBERSHIP_NOT_FOUND,
        ErrorCode.GROUP_FULL,
    ),
)
async def set_member_status(
    group_id: int, user_id: int, body: MembershipStatusUpdate, session: SessionDep, access: AccessDep
) -> object:
    return await service.set_member_status(session, access, group_id, user_id, body.status)


@router.delete(
    "/{group_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a member",
    responses=errors(
        *AUTHED,
        ErrorCode.VALIDATION_ERROR,
        ErrorCode.NOT_GROUP_MEMBER,
        ErrorCode.NOT_GROUP_ADMIN,
        ErrorCode.MEMBERSHIP_NOT_FOUND,
    ),
)
async def remove_member(group_id: int, user_id: int, session: SessionDep, access: AccessDep) -> None:
    await service.remove_member(session, access, group_id, user_id)
