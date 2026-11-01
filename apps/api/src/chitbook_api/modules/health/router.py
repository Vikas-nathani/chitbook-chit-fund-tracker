from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from chitbook_api.core.deps import SessionDep
from chitbook_api.core.errors import errors
from chitbook_api.core.schemas import ApiModel
from chitbook_api.core.time import now

router = APIRouter(tags=["health"])


class Health(ApiModel):
    status: str
    time: str
    database: str | None = None


@router.get("/health", response_model=Health, summary="Liveness: the process is up", responses=errors())
async def health() -> Health:
    return Health(status="ok", time=now().isoformat())


@router.get(
    "/health/ready", response_model=Health, summary="Readiness: the database answers", responses=errors()
)
async def ready(session: SessionDep) -> Health:
    tz = await session.scalar(text("SELECT current_setting('TimeZone')"))
    return Health(status="ok", time=now().isoformat(), database=f"ok (timezone={tz})")
