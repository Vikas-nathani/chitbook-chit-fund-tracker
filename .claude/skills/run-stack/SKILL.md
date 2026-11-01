---
name: run-stack
description: Start, restart or check the ChitBook stack (API container, web container, host Postgres) and confirm it works end to end. Use when asked to run the app, after changes, or when something seems down.
---

# Run & check the stack

1. **Database** (host Postgres on 5432):

   ```bash
   pg_isready -h localhost -p 5432
   ```

   - If the app role can't log in, run `scripts/setup-db.sh`.
2. **Build and start:**

   ```bash
   docker compose up -d --build
   docker compose ps          # chitbook_api healthy, chitbook_web Up
   ```

3. **Health:**

   ```bash
   curl -s localhost:8080/health/ready     # database "ok (timezone=Asia/Kolkata)"
   curl -s -o /dev/null -w '%{http_code}\n' localhost:3500/
   ```

4. **End to end:**

   ```bash
   apps/api/.venv/bin/python scripts/smoke_test.py    # expects ALL PASSED
   ```

   - It covers login, refresh rotation and reuse, a full simple-chit flow, WebSocket chat and the error envelope.
5. **If anything fails:**
   - `docker compose logs --tail 100 api`
   - Then follow `/debug-api-error`.

Urls:
- web `http://<host>:3500`
- API `http://<host>:8080`
- Swagger `http://<host>:8080/api/docs`

Admin login: `ADMIN_USERNAME` / `ADMIN_PASSWORD` from `.env`. Ask the user; never print the password.
