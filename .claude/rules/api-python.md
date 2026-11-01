---
paths:
  - "apps/api/**/*.py"
---

# API (Python) rules

- **Layers:** router → service → repository → models. Routers never query; repositories never check access.
- **Every endpoint:**
  - `summary=` text, a `response_model`, and the right status (201 create, 204 delete).
  - An access check in the service (`Access`).
  - A test in `tests/integration/`.
- **Errors:** `raise AppError(ErrorCode.X)` or `AppError(ErrorCode.X, "specific message")`. Never `HTTPException`, never bare `Exception`.
- **Every route declares its errors** in the decorator: `responses=errors(*AUTHED, ErrorCode.VALIDATION_ERROR, ErrorCode.X)`. `DB_UNAVAILABLE` / `INTERNAL_ERROR` are added automatically.
- **Logs go to stdout only** (`docker compose logs api`). Never add file handlers.
- **Logs:** `log = structlog.get_logger("chitbook.<module>")`, then `log.info("<module>.<past_tense_event>", entity_id=...)`. Use warning for rejected or security events.
- **No defaults for settings.** Read them via `get_settings()` only.
- **Time:** `from chitbook_api.core.time import now, today, YearMonth`.
- **Money:** `Decimal` in, `Money` out. Quantize with `ROUND_HALF_UP` to `0.01`.
- **Typing:** fully typed; `mypy --strict` must pass. Don't add `Any` where a real type exists.
- **Schema changes** need an Alembic migration (see `/db-migration`), and then `scripts/gen-docs.sh`.
