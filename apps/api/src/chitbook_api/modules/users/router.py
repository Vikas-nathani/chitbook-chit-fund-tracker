from __future__ import annotations

from fastapi import APIRouter, status

from chitbook_api.core.deps import AccessDep, SessionDep
from chitbook_api.core.errors import AUTHED, ErrorCode, errors
from chitbook_api.modules.users import service
from chitbook_api.modules.users.schemas import PasswordChange, UserOut, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])

# Users may read/change only themselves unless they are a platform admin
SELF_ONLY = (ErrorCode.FORBIDDEN, ErrorCode.USER_NOT_FOUND)


@router.get("", response_model=list[UserOut], summary="List users visible to me", responses=errors(*AUTHED))
async def list_users(session: SessionDep, access: AccessDep) -> object:
    return await service.list_visible(session, access)


@router.get(
    "/by-username/{username}",
    response_model=UserOut,
    summary="Get a user by username",
    responses=errors(*AUTHED, ErrorCode.VALIDATION_ERROR, *SELF_ONLY),
)
async def get_user_by_username(username: str, session: SessionDep, access: AccessDep) -> object:
    return await service.get_by_username(session, access, username)


@router.get(
    "/{user_id}",
    response_model=UserOut,
    summary="Get a user",
    responses=errors(*AUTHED, ErrorCode.VALIDATION_ERROR, *SELF_ONLY),
)
async def get_user(user_id: int, session: SessionDep, access: AccessDep) -> object:
    return await service.get(session, access, user_id)


@router.patch(
    "/{user_id}",
    response_model=UserOut,
    summary="Update name, phone or email",
    responses=errors(*AUTHED, ErrorCode.VALIDATION_ERROR, *SELF_ONLY, ErrorCode.EMAIL_TAKEN),
)
async def update_user(user_id: int, body: UserUpdate, session: SessionDep, access: AccessDep) -> object:
    return await service.update_profile(session, access, user_id, body)


@router.put(
    "/{user_id}/password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Change password",
    responses=errors(
        *AUTHED,
        ErrorCode.VALIDATION_ERROR,
        *SELF_ONLY,
        ErrorCode.AUTH_WRONG_CURRENT_PASSWORD,
        ErrorCode.AUTH_WEAK_PASSWORD,
    ),
)
async def change_password(user_id: int, body: PasswordChange, session: SessionDep, access: AccessDep) -> None:
    await service.change_password(session, access, user_id, body)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a user",
    responses=errors(*AUTHED, ErrorCode.VALIDATION_ERROR, *SELF_ONLY),
)
async def delete_user(user_id: int, session: SessionDep, access: AccessDep) -> None:
    await service.delete(session, access, user_id)
