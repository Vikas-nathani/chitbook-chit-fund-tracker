---
paths:
  - "apps/api/migrations/**"
  - "apps/api/src/chitbook_api/modules/*/models.py"
---

# Database migration rules

- Never edit a committed migration. Add a new revision.
- **Generate:** from `apps/api`, run `DB_HOST=localhost uv run --env-file ../../.env alembic revision --autogenerate -m "<what changed>"`.
- **Review every generated file:**
  - Autogenerate misses renames: it produces a drop + add, which loses data. Hand-write `op.alter_column` / `op.rename_table` instead.
  - Add `server_default` when adding a NOT NULL column to a table that already has rows.
  - Write a working `downgrade()`.
- Money columns are `Numeric(14, 2)` and time columns are `DateTime(timezone=True)`.
- After applying: run `uv run pytest` (tests rebuild the schema from migrations) and `scripts/gen-docs.sh`.
