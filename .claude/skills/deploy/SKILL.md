---
name: deploy
description: Deploy or update the ChitBook API and web app on the server with docker compose (pull/build, migrate, restart, verify, roll back). Use when asked to deploy, release the backend, or apply changes to the running server.
---

# Deploy (server)

Before you start:
- All tests pass (API + app).
- Docs are regenerated (`scripts/gen-docs.sh`, then `--check` is clean).
- The changes are committed.

1. **Back up the database** first:

   ```bash
   mkdir -p backups
   PGPASSWORD=... pg_dump -h localhost -U chitbook_app -Fc chitbook > backups/chitbook-$(date +%Y%m%d-%H%M).dump
   ```

   - Take the password from `.env`; never print it.
2. **New settings?** Compare `.env` with `.env.example`. Every variable must be set; the app refuses to start otherwise.
3. **Build and restart:**

   ```bash
   docker compose up -d --build
   ```

   - The API container runs `alembic upgrade head` before it starts serving.
4. **Verify:**

   ```bash
   docker compose ps
   curl -s localhost:8080/health/ready
   apps/api/.venv/bin/python scripts/smoke_test.py
   docker compose logs --tail 50 api | grep -E '"level": "(error|warning)"'
   ```

5. **Roll back:**
   - Code: `git checkout <previous-commit> && docker compose up -d --build`.
   - Schema: `DB_HOST=localhost uv run --env-file ../../.env alembic downgrade <rev>` from `apps/api`, or restore the dump with `pg_restore -c`.

For production, put an HTTPS reverse proxy in front and keep 8080 private (`docs/auth.md`, hardening checklist). Confirm with the user before deploying.
