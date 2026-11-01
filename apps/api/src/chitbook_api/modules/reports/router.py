from __future__ import annotations

from fastapi import APIRouter

from chitbook_api.core.deps import AccessDep, SessionDep
from chitbook_api.core.errors import AUTHED, ErrorCode, errors
from chitbook_api.modules.reports import service
from chitbook_api.modules.reports.schemas import AuditReport, GroupSummary, MemberGroupSummary

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get(
    "/group/{group_id}/audit",
    response_model=AuditReport,
    summary="Unverified payments (group admin)",
    responses=errors(
        *AUTHED,
        ErrorCode.VALIDATION_ERROR,
        ErrorCode.GROUP_NOT_FOUND,
        ErrorCode.NOT_GROUP_MEMBER,
        ErrorCode.NOT_GROUP_ADMIN,
    ),
)
async def audit_report(group_id: int, session: SessionDep, access: AccessDep) -> object:
    return await service.audit(session, access, group_id)


@router.get(
    "/group/{group_id}/summary",
    response_model=GroupSummary,
    summary="Group financial summary",
    responses=errors(
        *AUTHED, ErrorCode.VALIDATION_ERROR, ErrorCode.GROUP_NOT_FOUND, ErrorCode.NOT_GROUP_MEMBER
    ),
)
async def group_summary(group_id: int, session: SessionDep, access: AccessDep) -> object:
    return await service.group_summary(session, access, group_id)


@router.get(
    "/user/{user_id}",
    response_model=list[MemberGroupSummary],
    summary="A member's summary per group",
    responses=errors(*AUTHED, ErrorCode.VALIDATION_ERROR, ErrorCode.FORBIDDEN),
)
async def member_summaries(user_id: int, session: SessionDep, access: AccessDep) -> object:
    return await service.member_summaries(session, access, user_id)
