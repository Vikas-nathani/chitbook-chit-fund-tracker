---
name: db-migration
description: Create, review, apply or roll back a ChitBook database schema change with Alembic on the host Postgres. Use whenever a SQLAlchemy model in apps/api changes.
---

# Database migration

From `apps/api`. `DB_HOST=localhost` because these commands run on the host, not in Docker.

1. Edit the model(s) in `src/chitbook_api/modules/<module>/models.py`.
2. Generate:

   ```bash
   DB_HOST=localhost uv run --env-file ../../.env alembic revision --autogenerate -m "add phone to members"
   ```

3. **Review** the new file in `migrations/versions/`:
   - Renames come out as drop + add, which loses data. Rewrite them as `op.alter_column(..., new_column_name=...)` / `op.rename_table`.
   - A new NOT NULL column on an existing table needs a `server_default=` (or add it nullable, backfill, then alter).
   - Check that the types are right: `Numeric(14, 2)` for money, `DateTime(timezone=True)` for times.
   - `downgrade()` must exactly undo `upgrade()`.
4. Apply locally:

   ```bash
   DB_HOST=localhost uv run --env-file ../../.env alembic upgrade head
   ```

5. Test: `uv run pytest`. The test DB is rebuilt from **all** migrations, so a broken migration fails here.
6. Regenerate docs: `scripts/gen-docs.sh` (`docs/database.md` changes).
7. Deploy: restarting the api container runs `alembic upgrade head` automatically.

**Roll back one step:** `DB_HOST=localhost uv run --env-file ../../.env alembic downgrade -1`

**Never** edit a migration that is already committed. A hook blocks it.
