from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, Response, status

from chitbook_api.core.deps import AccessDep, SessionDep
from chitbook_api.core.errors import AUTHED, ErrorCode, errors
from chitbook_api.core.time import now
from chitbook_api.modules.ledger import service
from chitbook_api.modules.ledger.schemas import LedgerCreate, LedgerOut

router = APIRouter(prefix="/ledger", tags=["ledger"])

GroupIdQuery = Annotated[int | None, Query(alias="groupId")]
UserIdQuery = Annotated[int | None, Query(alias="userId")]

# Search rules: no filter -> platform admin only; userId -> self, group admin or platform admin;
# groupId only -> group admin
SEARCH_ERRORS = (
    ErrorCode.ADMIN_REQUIRED,
    ErrorCode.FORBIDDEN,
    ErrorCode.NOT_GROUP_MEMBER,
    ErrorCode.NOT_GROUP_ADMIN,
)


@router.post(
    "",
    response_model=LedgerOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add a ledger entry",
    responses=errors(
        *AUTHED,
        ErrorCode.VALIDATION_ERROR,
        ErrorCode.GROUP_NOT_FOUND,
        ErrorCode.NOT_GROUP_MEMBER,
        ErrorCode.NOT_GROUP_ADMIN,
        ErrorCode.USER_NOT_FOUND,
    ),
)
async def create_entry(body: LedgerCreate, session: SessionDep, access: AccessDep) -> object:
    return await service.create(session, access, body)


@router.get(
    "",
    response_model=list[LedgerOut],
    summary="Search ledger entries by group and/or user",
    responses=errors(*AUTHED, ErrorCode.VALIDATION_ERROR, *SEARCH_ERRORS),
)
async def search_entries(
    session: SessionDep, access: AccessDep, group_id: GroupIdQuery = None, user_id: UserIdQuery = None
) -> object:
    return await service.search(session, access, group_id, user_id)


@router.get(
    "/pdf",
    response_class=Response,
    responses={
        200: {"content": {"application/pdf": {}}, "description": "PDF file"},
        **errors(*AUTHED, ErrorCode.VALIDATION_ERROR, *SEARCH_ERRORS),
    },
    summary="Download ledger entries as PDF",
)
async def export_pdf(
    session: SessionDep, access: AccessDep, group_id: GroupIdQuery = None, user_id: UserIdQuery = None
) -> Response:
    content = await service.export_pdf(session, access, group_id, user_id)
    filename = f"ledger-{now().strftime('%Y%m%d-%H%M')}.pdf"
    return Response(
        content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/{entry_id}",
    response_model=LedgerOut,
    summary="Get a ledger entry",
    responses=errors(
        *AUTHED,
        ErrorCode.VALIDATION_ERROR,
        ErrorCode.LEDGER_NOT_FOUND,
        ErrorCode.NOT_GROUP_MEMBER,
        ErrorCode.NOT_GROUP_ADMIN,
    ),
)
async def get_entry(entry_id: int, session: SessionDep, access: AccessDep) -> object:
    return await service.get(session, access, entry_id)
