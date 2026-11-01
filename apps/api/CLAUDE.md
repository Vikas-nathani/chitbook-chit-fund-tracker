# ChitBook API (FastAPI)

## Layers (keep them separate)

| File | Allowed | Not allowed |
|---|---|---|
| `router.py` | path/query/body parsing, `response_model`, status codes, calling **one** service function | queries, business rules |
| `service.py` | rules, `Access` checks, raising `AppError`, `log.info("module.event", ...)` | HTTP objects (except `Request` for audit) |
| `repository.py` | SQLAlchemy queries | rules, access checks |
| `models.py` | tables (`Base`, `TimestampMixin`, `NUMERIC` money, `DateTime(timezone=True)`) | logic |
| `schemas.py` | Pydantic `ApiModel` (camelCase); `Money` / `AppDateTime` for output | |

## Patterns to copy

- **Simple module:** `modules/auctions/` (create, get, list, delete, with group checks).
- **Owner-scoped data:** `modules/simple_chits/service.py`.
- **Auth/security:** `modules/auth/service.py`, `core/security.py`.

## Must-knows

- **Session dependency:**
  - `SessionDep` commits when the endpoint returns, **before** the response is sent. Don't call `session.commit()` in services.
  - Exception: when you must persist **and then** raise (see `auth.service.login`).
- **Access checks** (`core/deps.py`): `access.require_group_member(group_id)`, `require_group_admin`, `require_self_or_group_admin`, `require_self_or_platform_admin`, `require_platform_admin`.
- **Not found vs forbidden:** for owner-scoped resources, return `*_NOT_FOUND` rather than `FORBIDDEN`, so other owners' ids aren't revealed.
- **Relationships:** many-to-one uses `lazy="joined"` and collections use `lazy="selectin"`. Async has no lazy loading, so don't access unloaded attributes.
- **After `flush()`:** use `await session.refresh(obj)` to load server defaults (`created_at`, `updated_at`).
- **Time:** `core/time.py` only.
- **Query params:** camelCase on the wire, via `Annotated[int | None, Query(alias="groupId")]`.
- **Config:** add new settings to `core/config.py` with **no default**.

## Commands (from `apps/api`)

```bash
uv run pytest                     # unit + integration (needs host Postgres + .env)
uv run pytest tests/unit -q       # fast, no DB
uv run ruff check . && uv run ruff format . && uv run mypy
DB_HOST=localhost uv run --env-file ../../.env alembic revision --autogenerate -m "..."
DB_HOST=localhost uv run --env-file ../../.env uvicorn chitbook_api.main:app --reload --port 8000
```

## Tests

- `tests/conftest.py` resets the `chitbook_test` schema through migrations, then truncates every table before each test.
- Fixtures: `client`, `make_user("name")` (registered and signed in), `admin_headers`, `group_setup` (lead / member / outsider + group).
- Assert on `error.code`, not on message text.
