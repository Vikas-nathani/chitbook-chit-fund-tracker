"""FastAPI application factory."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from chitbook_api.core.config import get_settings
from chitbook_api.core.db import get_engine
from chitbook_api.core.errors import register_exception_handlers
from chitbook_api.core.logging import configure_logging
from chitbook_api.core.middleware import RequestContextMiddleware
from chitbook_api.modules.auctions.router import router as auctions_router
from chitbook_api.modules.auth.router import router as auth_router
from chitbook_api.modules.chat.hub import hub as chat_hub
from chitbook_api.modules.chat.router import router as chat_router
from chitbook_api.modules.funds.router import router as funds_router
from chitbook_api.modules.groups.router import router as groups_router
from chitbook_api.modules.health.router import router as health_router
from chitbook_api.modules.ledger.router import router as ledger_router
from chitbook_api.modules.loans.router import router as loans_router
from chitbook_api.modules.media.router import router as media_router
from chitbook_api.modules.notifications.router import router as notifications_router
from chitbook_api.modules.payments.router import router as payments_router
from chitbook_api.modules.polls.router import router as polls_router
from chitbook_api.modules.reports.router import router as reports_router
from chitbook_api.modules.simple_chits.router import router as simple_chits_router
from chitbook_api.modules.users.bootstrap import ensure_admin
from chitbook_api.modules.users.router import router as users_router

API_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    log = structlog.get_logger("chitbook.app")
    settings = get_settings()
    log.info("app.starting", env=settings.app_env, tz=settings.tz)
    await ensure_admin()
    await chat_hub.start()
    log.info("app.started")
    yield
    await chat_hub.stop()
    await get_engine().dispose()
    log.info("app.stopped")


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings)

    app = FastAPI(
        title="ChitBook API",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/api/docs" if settings.api_docs_enabled else None,
        redoc_url=None,
        openapi_url="/api/openapi.json" if settings.api_docs_enabled else None,
    )
    register_exception_handlers(app)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-Chitbook-Client"],
        expose_headers=["X-Request-ID"],
    )
    # Added last = outermost: wraps CORS and every handler
    app.add_middleware(RequestContextMiddleware)

    app.include_router(health_router)
    api = APIRouter(prefix=API_PREFIX)
    for router in (
        auth_router,
        users_router,
        simple_chits_router,
        groups_router,
        funds_router,
        payments_router,
        ledger_router,
        auctions_router,
        loans_router,
        reports_router,
        notifications_router,
        polls_router,
        media_router,
        chat_router,
    ):
        api.include_router(router)
    app.include_router(api)
    return app


app = create_app()
