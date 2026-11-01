from __future__ import annotations

from fastapi import APIRouter, status

from chitbook_api.core.deps import AccessDep, SessionDep
from chitbook_api.core.errors import AUTHED, ErrorCode, errors
from chitbook_api.modules.media import service
from chitbook_api.modules.media.schemas import MediaCreate, MediaOut

router = APIRouter(prefix="/media", tags=["media"])


@router.post(
    "",
    response_model=MediaOut,
    status_code=status.HTTP_201_CREATED,
    summary="Share a photo/video link",
    responses=errors(
        *AUTHED, ErrorCode.VALIDATION_ERROR, ErrorCode.GROUP_NOT_FOUND, ErrorCode.NOT_GROUP_MEMBER
    ),
)
async def share_media(body: MediaCreate, session: SessionDep, access: AccessDep) -> object:
    return await service.create(session, access, body)


@router.get(
    "/group/{group_id}",
    response_model=list[MediaOut],
    summary="A group's shared media",
    responses=errors(*AUTHED, ErrorCode.VALIDATION_ERROR, ErrorCode.NOT_GROUP_MEMBER),
)
async def group_media(group_id: int, session: SessionDep, access: AccessDep) -> object:
    return await service.list_for_group(session, access, group_id)


@router.delete(
    "/{media_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete shared media",
    responses=errors(
        *AUTHED,
        ErrorCode.VALIDATION_ERROR,
        ErrorCode.MEDIA_NOT_FOUND,
        ErrorCode.NOT_GROUP_MEMBER,
        ErrorCode.NOT_GROUP_ADMIN,
    ),
)
async def delete_media(media_id: int, session: SessionDep, access: AccessDep) -> None:
    await service.delete(session, access, media_id)
