"""Credit/debit ledger per member per group, plus PDF export."""

from __future__ import annotations

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from chitbook_api.core.deps import Access
from chitbook_api.core.errors import AppError, ErrorCode
from chitbook_api.core.time import now
from chitbook_api.modules.groups.service import require_group
from chitbook_api.modules.ledger import pdf, repository
from chitbook_api.modules.ledger.models import LedgerEntry
from chitbook_api.modules.ledger.schemas import LedgerCreate, LedgerOut
from chitbook_api.modules.users import repository as users_repo

log = structlog.get_logger("chitbook.ledger")


def to_out(e: LedgerEntry) -> LedgerOut:
    return LedgerOut(
        id=e.id, entry_type=e.entry_type, amount=e.amount, entry_date=e.entry_date, remark=e.remark,
        reference_id=e.reference_id, user_id=e.user_id, user_name=e.user.name, chit_group_id=e.chit_group_id,
        chit_group_name=e.group.name, created_at=e.created_at, updated_at=e.updated_at,
    )  # fmt: skip


async def create(session: AsyncSession, access: Access, data: LedgerCreate) -> LedgerOut:
    await require_group(session, data.chit_group_id)
    await access.require_group_admin(data.chit_group_id)
    if await users_repo.get_by_id(session, data.user_id) is None:
        raise AppError(ErrorCode.USER_NOT_FOUND)
    entry = LedgerEntry(
        user_id=data.user_id,
        chit_group_id=data.chit_group_id,
        entry_type=data.entry_type,
        amount=data.amount,
        entry_date=data.entry_date or now(),
        remark=data.remark,
        reference_id=data.reference_id,
    )
    session.add(entry)
    await session.flush()
    await session.refresh(entry)
    log.info(
        "ledger.entry_created", entry_id=entry.id, group_id=data.chit_group_id, type=data.entry_type.value
    )
    return to_out(entry)


async def get(session: AsyncSession, access: Access, entry_id: int) -> LedgerOut:
    entry = await repository.get(session, entry_id)
    if entry is None:
        raise AppError(ErrorCode.LEDGER_NOT_FOUND)
    await access.require_self_or_group_admin(entry.user_id, entry.chit_group_id)
    return to_out(entry)


async def _check_scope(access: Access, group_id: int | None, user_id: int | None) -> None:
    """group+user: that member or a group admin; group: group admin; user: self; none: platform admin."""
    if group_id is not None and user_id is not None:
        await access.require_self_or_group_admin(user_id, group_id)
    elif group_id is not None:
        await access.require_group_admin(group_id)
    elif user_id is not None:
        access.require_self_or_platform_admin(user_id)
    else:
        access.require_platform_admin()


async def search(
    session: AsyncSession, access: Access, group_id: int | None, user_id: int | None
) -> list[LedgerOut]:
    await _check_scope(access, group_id, user_id)
    return [to_out(e) for e in await repository.search(session, group_id, user_id)]


async def export_pdf(
    session: AsyncSession, access: Access, group_id: int | None, user_id: int | None
) -> bytes:
    await _check_scope(access, group_id, user_id)
    entries = await repository.search(session, group_id, user_id)
    title = "Ledger Report"
    if group_id is not None and entries:
        title += f" - {entries[0].group.name}"
    log.info("ledger.pdf_exported", group_id=group_id, user_id=user_id, entries=len(entries))
    return pdf.render(entries, title)
