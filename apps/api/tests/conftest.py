"""Test fixtures.

Tests run against the real Postgres test database (DB_TEST_NAME from the repo .env) with the
schema built by the Alembic migrations, so migrations are tested too. Every test starts with
empty tables plus the bootstrap admin.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Awaitable, Callable
from pathlib import Path
from typing import Any

import pytest
from dotenv import dotenv_values

REPO_ROOT = Path(__file__).resolve().parents[3]
_env = dotenv_values(REPO_ROOT / ".env")
os.environ.update({k: v for k, v in _env.items() if v is not None})
# Tests talk to the host Postgres directly and use the throwaway test database
os.environ["DB_HOST"] = "localhost"
os.environ["DB_NAME"] = os.environ["DB_TEST_NAME"]
os.environ["ALEMBIC_DB_NAME"] = os.environ["DB_TEST_NAME"]
os.environ["API_DOCS_ENABLED"] = "true"

import asyncpg  # noqa: E402
import httpx  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from asgi_lifespan import LifespanManager  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from sqlalchemy import text  # noqa: E402

from chitbook_api.core.config import get_settings  # noqa: E402
from chitbook_api.core.db import get_engine  # noqa: E402
from chitbook_api.core.rate_limit import limiter  # noqa: E402
from chitbook_api.main import create_app  # noqa: E402
from chitbook_api.modules.users.bootstrap import ensure_admin  # noqa: E402
from tests import sql_trace  # noqa: E402

API_DIR = Path(__file__).resolve().parents[1]
ADMIN = {"username": os.environ["ADMIN_USERNAME"], "password": os.environ["ADMIN_PASSWORD"]}


async def _reset_schema() -> None:
    s = get_settings()
    conn = await asyncpg.connect(
        host=s.db_host,
        port=s.db_port,
        user=s.db_user,
        password=s.db_password.get_secret_value(),
        database=s.db_name,
    )
    await conn.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
    await conn.close()


@pytest.fixture(scope="session")
def _migrated_database() -> None:
    import asyncio

    asyncio.run(_reset_schema())
    cfg = Config(str(API_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(API_DIR / "migrations"))
    command.upgrade(cfg, "head")


@pytest.fixture(scope="session")
async def app(_migrated_database: None) -> AsyncIterator[FastAPI]:
    application = create_app()
    trace_path = os.environ.get("TRACE_SQL_TABLES")  # used by scripts/gen_api_docs.py
    if trace_path:
        sql_trace.install(application, get_engine())
    async with LifespanManager(application):
        yield application
    if trace_path:
        sql_trace.dump(trace_path)


@pytest.fixture(autouse=True)
async def _clean_tables(app: FastAPI) -> None:
    async with get_engine().begin() as conn:
        tables = (
            await conn.execute(
                text(
                    "SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename <> 'alembic_version'"
                )
            )
        ).scalars()
        await conn.execute(text(f"TRUNCATE {', '.join(tables)} RESTART IDENTITY CASCADE"))
    limiter.reset()
    await ensure_admin()


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


LoginFn = Callable[..., Awaitable[dict[str, Any]]]


@pytest.fixture
def login(client: httpx.AsyncClient) -> LoginFn:
    async def _login(username: str, password: str, **extra: Any) -> dict[str, Any]:
        r = await client.post(
            "/api/v1/auth/login", json={"username": username, "password": password, **extra}
        )
        assert r.status_code == 200, r.text
        return r.json()  # type: ignore[no-any-return]

    return _login


@pytest.fixture
def make_user(client: httpx.AsyncClient, login: LoginFn) -> Callable[[str], Awaitable[dict[str, Any]]]:
    """Registers + signs in a user; returns {"user": ..., "headers": {...}}."""

    async def _make(username: str) -> dict[str, Any]:
        password = f"{username}-Pass123"
        r = await client.post(
            "/api/v1/auth/register",
            json={"name": username.title(), "username": username, "email": f"{username}@example.com",
                  "password": password},
        )  # fmt: skip
        assert r.status_code == 201, r.text
        tokens = await login(username, password)
        return {"user": tokens["user"], "headers": {"Authorization": f"Bearer {tokens['accessToken']}"},
                "tokens": tokens, "password": password}  # fmt: skip

    return _make


@pytest.fixture
async def admin_headers(login: LoginFn) -> dict[str, str]:
    tokens = await login(ADMIN["username"], ADMIN["password"])
    return {"Authorization": f"Bearer {tokens['accessToken']}"}
