"""Creates the platform admin from ADMIN_* settings on startup if it does not exist yet."""

from __future__ import annotations

import structlog
from sqlalchemy.exc import IntegrityError

from chitbook_api.core.config import get_settings
from chitbook_api.core.db import get_sessionmaker
from chitbook_api.core.errors import AppError, ErrorCode
from chitbook_api.modules.users import repository, service
from chitbook_api.modules.users.models import UserRole
from chitbook_api.modules.users.schemas import UserCreate

log = structlog.get_logger("chitbook.bootstrap")


async def ensure_admin() -> None:
    s = get_settings()
    async with get_sessionmaker()() as session:
        if await repository.get_by_username(session, s.admin_username):
            log.info("admin.exists", username=s.admin_username)
            return
        # model_construct: the admin email may use a private domain (e.g. *.local) that public
        # sign-up validation rejects; the password policy is still enforced by service.register
        data = UserCreate.model_construct(
            name=s.admin_name,
            username=s.admin_username,
            email=s.admin_email,
            password=s.admin_password.get_secret_value(),
        )
        try:
            await service.register(session, data, role=UserRole.ADMIN)
            await session.commit()
        except (IntegrityError, AppError) as exc:
            # Several API workers start at once; another one created the admin first.
            # Anything else (e.g. ADMIN_PASSWORD failing the policy) must stop startup.
            already_exists = (ErrorCode.USERNAME_TAKEN, ErrorCode.EMAIL_TAKEN)
            if isinstance(exc, AppError) and exc.code not in already_exists:
                raise
            await session.rollback()
            log.info("admin.exists", username=s.admin_username)
            return
        log.info("admin.created", username=s.admin_username)
