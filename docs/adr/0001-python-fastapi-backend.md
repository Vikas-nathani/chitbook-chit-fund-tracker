# ADR 0001: Python + FastAPI backend

- **Status:** accepted · 2026-11-01

## Context

- The team works in Python, not Java.
- The API serves a mobile app and a web app, and needs typed request/response contracts.

## Decision

- **FastAPI**, with Pydantic v2 for schemas.
- **SQLAlchemy 2.0** (async, asyncpg) for the database, and **Alembic** for migrations.
- **uv** for dependencies, **ruff** for lint/format, **mypy** (strict) for types, **pytest** for tests, run against real Postgres.
- Module layout per feature: `models → repository → service → router`.

## Consequences

- OpenAPI is generated automatically. It feeds the app's TypeScript types and these docs.
- Async I/O handles many concurrent phones with few workers.
- Business rules live in `service.py` and are unit- and integration-tested.
