"""Records which database tables every API endpoint reads and writes while the tests run.

Enabled with TRACE_SQL_TABLES=<output.json>. scripts/gen_api_docs.py turns the result into the
"Database" part of each endpoint in docs/api/. Data comes from the real SQL the endpoint ran,
so it cannot drift from the code. (ON DELETE CASCADE effects happen inside Postgres and are
listed separately in the docs.)
"""

from __future__ import annotations

import contextvars
import json
import re
from collections import defaultdict
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request, Response
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine

_current_scope: contextvars.ContextVar[dict[str, Any] | None] = contextvars.ContextVar("scope", default=None)
_WRITE = re.compile(r"^\s*(?:INSERT\s+INTO|UPDATE|DELETE\s+FROM)\s+\"?(\w+)", re.IGNORECASE)
_READ = re.compile(r"\b(?:FROM|JOIN)\s+\"?(\w+)", re.IGNORECASE)
_SKIP = {"pg_tables", "pg_catalog", "alembic_version"}

_tables: dict[str, dict[str, set[str]]] = defaultdict(lambda: {"read": set(), "write": set()})


def _endpoint_key(scope: dict[str, Any]) -> str | None:
    route = scope.get("route")
    return f"{scope.get('method')} {route.path}" if route is not None else None


def install(app: FastAPI, engine: AsyncEngine) -> None:
    @app.middleware("http")
    async def remember_scope(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        token = _current_scope.set(request.scope)
        try:
            return await call_next(request)
        finally:
            _current_scope.reset(token)

    @event.listens_for(engine.sync_engine, "before_cursor_execute")
    def record(_conn: Any, _cursor: Any, statement: str, *_args: Any) -> None:
        scope = _current_scope.get()
        key = _endpoint_key(scope) if scope else None
        if key is None:
            return
        entry = _tables[key]  # recorded even when no table is touched (e.g. /health/ready)
        written = _WRITE.match(statement)
        if written:
            entry["write"].add(written.group(1))
        for table in _READ.findall(statement):
            if table not in _SKIP:
                entry["read"].add(table)


def dump(path: str) -> None:
    data = {k: {"read": sorted(v["read"]), "write": sorted(v["write"])} for k, v in sorted(_tables.items())}
    Path(path).write_text(json.dumps(data, indent=2) + "\n")
