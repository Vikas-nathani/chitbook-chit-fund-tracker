"""Generates the API reference in docs/api/ and the table reference in docs/database.md.

Everything comes from the code, so the docs cannot drift:
- routes, auth, request/response schemas      -> the FastAPI app + its OpenAPI schema
- example JSON                                -> built from those schemas
- router / service functions with file:line   -> Python source (inspect + ast)
- error codes per endpoint                    -> `responses=errors(...)` on each route in its router.py,
                                                 checked against the ErrorCodes reachable from the router
                                                 function (a mismatch fails the run)
- log events per endpoint                     -> log.* calls reachable from the router function
- tables read / written per endpoint          -> real SQL recorded during the test run (tests/sql_trace.py)

Usage (repo root):
    scripts/gen-docs.sh            # runs the tests with SQL tracing, then this script
    apps/api/.venv/bin/python scripts/gen_api_docs.py --check   # fail if docs are out of date
"""

from __future__ import annotations

import argparse
import ast
import inspect
import json
import os
import sys
import textwrap
import types
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
API_SRC = REPO / "apps" / "api" / "src"
DOCS = REPO / "docs"
TABLES_JSON = DOCS / "api" / ".endpoint-tables.json"

sys.path.insert(0, str(API_SRC))
# The app reads settings at import; docs generation needs no real database
from dotenv import dotenv_values  # noqa: E402

os.environ.update({k: v for k, v in dotenv_values(REPO / ".env").items() if v is not None})

from fastapi.routing import APIRoute, _iter_included_route_candidates  # noqa: E402

from chitbook_api.core import deps  # noqa: E402
from chitbook_api.core.db import Base  # noqa: E402
from chitbook_api.core.errors import ALWAYS, AUTHED, ErrorCode, declared_codes  # noqa: E402
from chitbook_api.main import create_app  # noqa: E402

AUTH_CODES = [c.name for c in AUTHED]
ALWAYS_CODES = [c.name for c in ALWAYS]
AUTH_CHECK_TABLES = {"auth_sessions", "users"}
FULL_PATH: dict[int, str] = {}  # id(route) -> path including /api/v1, filled by build()
MISMATCHES: list[str] = []  # routes whose responses=errors(...) disagree with the code


def full_path(route: APIRoute) -> str:
    return FULL_PATH.get(id(route), route.path)

TITLES = {
    "auth": "Auth & sessions",
    "users": "Users",
    "simple-chits": "Simple chits",
    "groups": "Chit groups & memberships",
    "funds": "Funds",
    "payments": "Payments",
    "ledger": "Ledger",
    "auctions": "Auctions",
    "loans": "Loans",
    "reports": "Reports",
    "notifications": "Notifications",
    "polls": "Polls",
    "media": "Media",
    "chat": "Chat",
    "health": "Health",
}


# ---------------------------------------------------------------- source analysis


def rel(path: str | Path) -> str:
    return str(Path(path).resolve().relative_to(REPO))


def location(fn: Callable[..., Any]) -> tuple[str, int]:
    fn = inspect.unwrap(fn)
    return rel(inspect.getsourcefile(fn) or ""), inspect.getsourcelines(fn)[1]


def link(fn: Callable[..., Any], label: str | None = None) -> str:
    path, line = location(fn)
    return f"[`{label or fn.__qualname__}`](../../{path}#L{line}) ({path.split('/')[-1]}:{line})"


def _resolve(call: ast.Call, fn: Callable[..., Any]) -> Callable[..., Any] | None:
    """Maps a call node to a ChitBook function/method it refers to (or None)."""
    g = getattr(inspect.unwrap(fn), "__globals__", {})
    target: Any = None
    f = call.func
    if isinstance(f, ast.Name):
        target = g.get(f.id)
    elif isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name):
        owner = f.value.id
        if owner in ("access", "self") and hasattr(deps.Access, f.attr):
            target = getattr(deps.Access, f.attr)
        elif isinstance(g.get(owner), types.ModuleType):
            target = getattr(g[owner], f.attr, None)
    if isinstance(target, property):
        target = target.fget
    if callable(target) and getattr(target, "__module__", "").startswith("chitbook_api"):
        if inspect.isfunction(target) or inspect.ismethod(target):
            return target  # type: ignore[no-any-return]
    return None


def walk(root: Callable[..., Any]) -> tuple[list[Callable[..., Any]], list[str], list[str]]:
    """All ChitBook functions reachable from `root`, the ErrorCodes they raise, and log events."""
    seen: dict[Any, None] = {}
    codes: dict[str, None] = {}
    events: dict[str, None] = {}
    stack = [root]
    while stack:
        fn = inspect.unwrap(stack.pop())
        if fn in seen:
            continue
        seen[fn] = None
        try:
            tree = ast.parse(textwrap.dedent(inspect.getsource(fn)))
        except (OSError, TypeError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "ErrorCode":
                codes[node.attr] = None
            if isinstance(node, ast.Call):
                f = node.func
                if (
                    isinstance(f, ast.Attribute)
                    and isinstance(f.value, ast.Name)
                    and f.value.id == "log"
                    and node.args
                    and isinstance(node.args[0], ast.Constant)
                ):
                    events[f"{node.args[0].value} ({f.attr})"] = None
                target = _resolve(node, fn)
                if target is not None:
                    stack.append(target)
    return list(seen), list(codes), list(events)


# ---------------------------------------------------------------- schema examples


def example_for(schema: dict[str, Any], spec: dict[str, Any], name: str = "", depth: int = 0) -> Any:
    if "$ref" in schema:
        return example_for(spec["components"]["schemas"][schema["$ref"].split("/")[-1]], spec, name, depth)
    for key in ("anyOf", "oneOf"):
        if key in schema:
            options = [s for s in schema[key] if s.get("type") != "null"]
            return example_for(options[0], spec, name, depth) if options else None
    if "enum" in schema:
        return schema["enum"][0]
    t = schema.get("type")
    n = name.lower()
    if t == "object" or "properties" in schema:
        if depth > 4:
            return {}
        return {k: example_for(v, spec, k, depth + 1) for k, v in schema.get("properties", {}).items()}
    if t == "array":
        return [example_for(schema.get("items", {}), spec, name, depth + 1)]
    if t == "boolean":
        return n not in {"paid", "verified", "current"} and not n.startswith("is")
    if t == "integer":
        return {"months": 20, "month": 5, "shares": 2, "duration": 20, "totalmembers": 20}.get(n, 1)
    if t == "number":
        if "percent" in n or "rate" in n:
            return 5.0
        return 25000.0
    fmt = schema.get("format", "")
    if fmt == "date-time" or n.endswith("at") or n.endswith("date"):
        return "2026-08-01T10:30:00+05:30"
    if fmt == "date" or n == "paidon":
        return "2026-08-01"
    if fmt == "email" or "email" in n:
        return "ravi@example.com"
    if fmt == "uuid" or n == "id":
        return "8f6c1c1e-2d4b-4b8e-9a0e-3f5d2c7b9a11"
    if fmt == "uri":
        return "https://example.com/photo.jpg"
    samples = {
        "username": "ravi", "password": "Ravi-pass-2026", "currentpassword": "Old-pass-1",
        "newpassword": "New-pass-2026", "name": "Ravi Kumar", "membername": "Ramesh", "startmonth": "2026-08",
        "calendarmonth": "2026-09", "month": "2026-08", "groupcode": "CHIT3F5A7C", "phone": "9876543210",
        "devicename": "Android app", "accesstoken": "eyJhbGciOiJIUzI1NiIs...", "refreshtoken": "q7k8B9XG...",
        "tokentype": "Bearer", "content": "Meeting at 7pm", "question": "Meet on Sunday?", "caption": "Monthly meeting",
        "mode": "UPI", "remark": "August contribution", "code": "CHIT_NOT_FOUND",
    }  # fmt: skip
    return samples.get(n, "string")


def body_schema(op: dict[str, Any]) -> dict[str, Any] | None:
    content = op.get("requestBody", {}).get("content", {})
    return content.get("application/json", {}).get("schema")


def response_schema(op: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
    for status, resp in op.get("responses", {}).items():
        if status.startswith("2"):
            schema = resp.get("content", {}).get("application/json", {}).get("schema")
            return status, schema
    return "200", None


def schema_name(schema: dict[str, Any] | None) -> str:
    if not schema:
        return "–"
    if "$ref" in schema:
        return f"`{schema['$ref'].split('/')[-1]}`"
    if schema.get("type") == "array":
        return f"list of {schema_name(schema.get('items'))}"
    return "JSON"


def fields_table(schema: dict[str, Any] | None, spec: dict[str, Any]) -> str:
    if not schema:
        return ""
    if schema.get("type") == "array":
        schema = schema.get("items", {})
    if "$ref" in schema:
        schema = spec["components"]["schemas"][schema["$ref"].split("/")[-1]]
    props = schema.get("properties", {})
    if not props:
        return ""
    required = set(schema.get("required", []))
    rows = ["| Field | Type | Required | Notes |", "|---|---|---|---|"]
    for key, prop in props.items():
        rows.append(f"| `{key}` | {type_label(prop)} | {'yes' if key in required else 'no'} | {constraint(prop)} |")
    return "\n".join(rows)


def type_label(prop: dict[str, Any]) -> str:
    if "$ref" in prop:
        return prop["$ref"].split("/")[-1]
    if "anyOf" in prop:
        return " or ".join(type_label(p) for p in prop["anyOf"])
    if prop.get("type") == "array":
        return f"list[{type_label(prop.get('items', {}))}]"
    if "enum" in prop:
        return " / ".join(map(str, prop["enum"]))
    return str(prop.get("format") or prop.get("type", "any"))


def constraint(prop: dict[str, Any]) -> str:
    parts = []
    for key in ("minLength", "maxLength", "minimum", "maximum", "exclusiveMinimum", "pattern"):
        if key in prop:
            parts.append(f"{key}={prop[key]}")
    for sub in prop.get("anyOf", []):
        for key in ("minLength", "maxLength", "minimum", "maximum", "exclusiveMinimum", "pattern"):
            if key in sub:
                parts.append(f"{key}={sub[key]}")
    desc = prop.get("description", "")
    return "; ".join([*parts, desc] if desc else parts).replace("|", "\\|")


# ---------------------------------------------------------------- rendering


def endpoint_section(route: APIRoute, op: dict[str, Any], spec: dict[str, Any], tables: dict[str, Any]) -> str:
    method = sorted(route.methods)[0]
    path = full_path(route)
    dep_calls = {d.call for d in route.dependant.dependencies}
    flat_calls: set[Any] = set()
    stack = list(route.dependant.dependencies)
    while stack:
        d = stack.pop()
        flat_calls.add(d.call)
        stack.extend(d.dependencies)
    authed = deps.get_current_user in flat_calls
    rate_limited = any(getattr(c, "__qualname__", "").startswith("auth_rate_limit") for c in flat_calls | dep_calls)

    funcs, reachable, events = walk(route.endpoint)
    if authed:
        reachable = [*AUTH_CODES, *reachable]
    if body_schema(op) or route.dependant.query_params or route.dependant.path_params:
        reachable.append("VALIDATION_ERROR")
    if rate_limited:
        reachable.append("RATE_LIMITED")
    reachable = list(dict.fromkeys([*reachable, *ALWAYS_CODES]))

    # The router's responses=errors(...) is the source of truth; it must match what the code can raise
    codes = declared_codes(route.responses)
    missing = sorted(set(reachable) - set(codes))
    extra = sorted(set(codes) - set(reachable))
    if missing or extra:
        MISMATCHES.append(f"{link(route.endpoint)}: add {missing or '-'} / remove {extra or '-'}")
    codes.sort(key=lambda c: ErrorCode[c].status)  # stable: keeps the router's order within a status

    status, resp = response_schema(op)
    body = body_schema(op)
    traced = tables.get(f"{method} {route.path_format}")

    service_fns = [f for f in funcs if f is not route.endpoint and not f.__qualname__.startswith("Access.")]
    lines = [
        f"### `{method} {path}`",
        "",
        f"{route.summary or route.name}",
        "",
        f"- **Auth:** {'Bearer access token' if authed else 'public'}"
        + (" · rate limited per IP" if rate_limited else ""),
        f"- **Success:** `{status}` → {schema_name(resp)}",
        f"- **Router:** {link(route.endpoint)}",
    ]
    if service_fns:
        lines.append("- **Calls:** " + ", ".join(link(f) for f in service_fns[:8]))
    access_checks = [f.__name__ for f in funcs if f.__qualname__.startswith("Access.")]
    if access_checks:
        lines.append("- **Access checks:** " + ", ".join(f"`{a}`" for a in dict.fromkeys(access_checks)))
    lines.append("")

    params = op.get("parameters", [])
    if params:
        lines += ["**Parameters**", "", "| Name | In | Type | Required |", "|---|---|---|---|"]
        for p in params:
            lines.append(f"| `{p['name']}` | {p['in']} | {type_label(p.get('schema', {}))} | {'yes' if p.get('required') else 'no'} |")
        lines.append("")

    if body:
        lines += ["**Request body**", "", fields_table(body, spec), "", "```json",
                  json.dumps(example_for(body, spec), indent=2, ensure_ascii=False), "```", ""]  # fmt: skip
    if resp:
        example = example_for(resp, spec)
        text = json.dumps(example, indent=2, ensure_ascii=False)
        if len(text) > 2500:
            text = text[:2500] + "\n  ... (truncated)"
        lines += [f"**Response `{status}`**", "", fields_table(resp, spec), "", "```json", text, "```", ""]
    elif status == "204":
        lines += ["**Response `204`**: no body.", ""]

    if traced:
        data_tables = [t for t in traced["read"] if not (authed and t in AUTH_CHECK_TABLES and t not in traced["write"])]
        lines += [
            "**Database**",
            "",
            f"- Writes: {', '.join(f'`{t}`' for t in traced['write']) or '–'}",
            f"- Reads: {', '.join(f'`{t}`' for t in data_tables) or '–'}",
        ]
        if authed:
            lines.append("- Token check reads `auth_sessions` + `users` (every signed-in request)")
        if method == "DELETE":
            lines.append("- Child rows are removed by `ON DELETE CASCADE` (see docs/database.md)")
        lines.append("")
    else:
        lines += ["**Database**: no SQL recorded (the endpoint does not use the database, or no test calls it).", ""]

    service = service_fns[0] if service_fns else None
    writes = ", ".join(traced["write"]) if traced and traced["write"] else ""
    reads = ", ".join(t for t in (traced["read"] if traced else []) if t not in AUTH_CHECK_TABLES) or "-"
    def short(fn: Callable[..., Any]) -> str:  # e.g. router.save_payout
        return f"{fn.__module__.rsplit('.', 1)[-1]}.{fn.__qualname__}"

    lines += ["**Flow**", "", "```mermaid", "sequenceDiagram", "    participant C as Client",
              f"    participant R as {short(route.endpoint)}()"]  # fmt: skip
    if service:
        lines.append(f"    participant S as {short(service)}()")
    lines += ["    participant DB as Postgres", f"    C->>R: {method} {path}"]
    if authed:
        lines.append("    R->>DB: check token session (auth_sessions, users)")
    if service:
        lines += [f"    R->>S: {service.__name__}(...)"]
        if writes:
            lines.append(f"    S->>DB: write {writes}")
        lines += [f"    S->>DB: read {reads}", "    DB-->>S: rows", "    S-->>R: result"]
    else:
        lines.append(f"    R->>DB: read {reads}")
    lines += [f"    R-->>C: {status} {schema_name(resp).strip('`')}", "```", ""]

    lines += ["**Errors** (declared in the router with `responses=errors(...)`)", "",
              "| HTTP | Code | Message | Exact problem / fix |", "|---|---|---|---|"]  # fmt: skip
    for code in codes:
        ec = ErrorCode[code]
        lines.append(f"| {ec.status} | `{code}` | {ec.default_message} | {ec.cause} |")
    lines.append("")
    lines += ["**Diagnose**", "", "- Every response carries `X-Request-ID`; errors also return it as `error.requestId`.",
              "- `docker compose logs api | grep <request_id>` shows the access line (`http.request`) and any error lines.",
              "- Each error's exact problem is in the table above (from the router's `responses=errors(...)`)."]  # fmt: skip
    if events:
        lines.append("- Log events on success: " + ", ".join(f"`{e}`" for e in events))
    lines += ["- 500 / 503: see [logging & debugging](../operations/logging-and-debugging.md).", "", "---", ""]
    return "\n".join(lines)


def render_module(tag: str, routes: list[tuple[APIRoute, dict[str, Any]]], spec: dict[str, Any], tables: dict[str, Any]) -> str:
    title = TITLES.get(tag, tag.title())
    service_doc = ""
    mod = sys.modules.get(routes[0][0].endpoint.__module__.rsplit(".", 1)[0] + ".service")
    if mod and mod.__doc__:
        service_doc = mod.__doc__.strip()
    out = [
        f"# {title} API",
        "",
        "> Generated by `scripts/gen_api_docs.py` from the code. Do not edit by hand; run `scripts/gen-docs.sh`.",
        "",
    ]
    if service_doc:
        out += ["## Overview", "", *[f"> {line}" if line else ">" for line in service_doc.splitlines()], ""]
    out += ["## Endpoints", "", "| Method | Path | Summary |", "|---|---|---|"]
    for route, _ in routes:
        method = sorted(route.methods)[0]
        path = full_path(route)
        anchor = f"{method} {path}".lower().replace("/", "").replace("{", "").replace("}", "").replace(" ", "-")
        out.append(f"| {method} | [`{path}`](#{anchor}) | {route.summary or ''} |")
    out += ["", "## Details", ""]
    out += [endpoint_section(route, op, spec, tables) for route, op in routes]
    return "\n".join(out)


def render_index(groups: dict[str, list[tuple[APIRoute, dict[str, Any]]]]) -> str:
    out = ["# Endpoint index", "", "> Generated by `scripts/gen_api_docs.py`. Every route in the API, by module.", ""]
    total = sum(len(v) for v in groups.values())
    out += [f"**{total} HTTP endpoints** + 1 WebSocket (`/api/v1/chat/ws/groups/{{group_id}}`, see [chat](chat.md)).", ""]
    out += ["| Module | Method | Path | Auth | Summary |", "|---|---|---|---|---|"]
    for tag, routes in groups.items():
        for route, _ in routes:
            authed = any(d.call is deps.get_current_user for d in _flat(route))
            out.append(
                f"| [{TITLES.get(tag, tag)}]({tag}.md) | {sorted(route.methods)[0]} | `{full_path(route)}` | "
                f"{'token' if authed else 'public'} | {route.summary or ''} |"
            )
    return "\n".join(out) + "\n"


def _flat(route: APIRoute) -> Iterable[Any]:
    stack = list(route.dependant.dependencies)
    while stack:
        d = stack.pop()
        yield d
        stack.extend(d.dependencies)


def render_errors() -> str:
    out = ["# Error codes", "", "> Generated from `ErrorCode` in `apps/api/src/chitbook_api/core/errors.py`.", "",
           "Every error response:", "", "```json",
           '{"error": {"code": "CHIT_NOT_FOUND", "message": "Chit not found", "details": null, "requestId": "5f2c..."}}',
           "```", "", "| Code | HTTP | Message | Exact problem / fix |", "|---|---|---|---|"]  # fmt: skip
    for ec in ErrorCode:
        out.append(f"| `{ec.name}` | {ec.status} | {ec.default_message} | {ec.cause} |")
    return "\n".join(out) + "\n"


def render_database(tables: dict[str, Any]) -> str:
    md = Base.metadata
    out = ["# Database", "", "> Generated from the SQLAlchemy models (`apps/api/src/chitbook_api/modules/*/models.py`)",
           "> and the SQL recorded during tests. Schema changes go through Alembic migrations.", "",
           "- Engine: PostgreSQL 18 on the host (port 5432), database `chitbook`, role `chitbook_app`",
           "- Time: every timestamp is `timestamptz`; the role's session timezone is `Asia/Kolkata`",
           "- Money: `NUMERIC(14,2)`; percents `NUMERIC(5,2)`", "",
           "## Entity relationships", "", "```mermaid", "erDiagram"]  # fmt: skip
    for table in sorted(md.tables.values(), key=lambda t: t.name):
        for fk in sorted(table.foreign_keys, key=lambda f: f.parent.name):
            out.append(f"    {fk.column.table.name} ||--o{{ {table.name} : \"{fk.parent.name}\"")
    out += ["```", ""]
    used_by: dict[str, dict[str, list[str]]] = {}
    for key, rw in tables.items():
        for kind in ("read", "write"):
            for t in rw[kind]:
                used_by.setdefault(t, {"read": [], "write": []})[kind].append(key)
    for table in sorted(md.tables.values(), key=lambda t: t.name):
        out += [f"## `{table.name}`", "", "| Column | Type | Null | Key / default |", "|---|---|---|---|"]
        for col in table.columns:
            keys = []
            if col.primary_key:
                keys.append("PK")
            for fk in col.foreign_keys:
                keys.append(f"FK → {fk.column.table.name}.{fk.column.name} (on delete {fk.ondelete or 'NO ACTION'})")
            if col.unique:
                keys.append("unique")
            if col.identity is not None:
                keys.append("auto-increment")
            elif col.server_default is not None:
                keys.append(f"default {getattr(col.server_default, 'arg', col.server_default)}")
            out.append(f"| `{col.name}` | {col.type} | {'yes' if col.nullable else 'no'} | {'; '.join(keys)} |")
        extras = [c for c in table.constraints if c.__class__.__name__ == "UniqueConstraint" and len(c.columns) > 1]
        for c in sorted(extras, key=lambda c: str(c.name)):
            out.append(f"\nUnique together: {', '.join(f'`{col.name}`' for col in c.columns)}")
        idx = sorted(table.indexes, key=lambda i: str(i.name))
        if idx:
            out.append("\nIndexes: " + ", ".join(f"`{i.name}` ({', '.join(c.name for c in i.columns)})" for i in idx))
        usage = used_by.get(table.name)
        if usage:
            writers = sorted(set(usage["write"]))
            readers = sorted(set(usage["read"]) - set(writers))
            if writers:
                out.append("\nWritten by: " + ", ".join(f"`{w}`" for w in writers))
            if readers and table.name not in AUTH_CHECK_TABLES:
                out.append("\nRead by: " + ", ".join(f"`{r}`" for r in readers))
            if table.name in AUTH_CHECK_TABLES:
                out.append("\nRead by: every signed-in request (token/session check).")
        out.append("")
    return "\n".join(out)


def build() -> dict[Path, str]:
    app = create_app()
    spec = app.openapi()
    tables = json.loads(TABLES_JSON.read_text()) if TABLES_JSON.exists() else {}
    groups: dict[str, list[tuple[APIRoute, dict[str, Any]]]] = {}
    # FastAPI keeps included routers nested; this yields every effective route. Their `path` lacks
    # the include prefix (/api/v1), so the full path is taken from the OpenAPI document.
    for route in _iter_included_route_candidates(app.routes):
        if not isinstance(route, APIRoute):
            continue
        method = sorted(route.methods)[0].lower()
        full = next(p for p, ops in spec["paths"].items() if p.endswith(route.path_format) and method in ops)
        FULL_PATH[id(route)] = full
        tag = (route.tags or ["misc"])[0]
        groups.setdefault(str(tag), []).append((route, spec["paths"][full][method]))
    files = {DOCS / "api" / f"{tag}.md": render_module(tag, routes, spec, tables) + "\n" for tag, routes in groups.items()}
    files[DOCS / "api" / "endpoints.md"] = render_index(groups)
    files[DOCS / "api" / "errors.md"] = render_errors()
    files[DOCS / "database.md"] = render_database(tables) + "\n"
    return files


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="exit 1 if any generated doc is out of date")
    args = parser.parse_args()
    files = build()
    if MISMATCHES:
        print("Routes whose responses=errors(...) do not match the errors their code can raise:")
        print("\n".join(f"  {m}" for m in MISMATCHES))
        sys.exit(1)
    stale =[p for p, text in files.items() if not p.exists() or p.read_text() != text]
    if args.check:
        for p in stale:
            print(f"out of date: {rel(p)}")
        sys.exit(1 if stale else 0)
    for p, text in files.items():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    print(f"wrote {len(files)} files ({len(stale)} changed)")


if __name__ == "__main__":
    main()
