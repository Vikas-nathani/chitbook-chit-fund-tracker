---
name: debug-api-error
description: Diagnose a failing ChitBook API call (4xx, 500, 503, timeouts, app showing an error) using the request id, structured logs and the error-code catalogue. Use when the user reports an error or an endpoint misbehaves.
---

# Debug an API error

1. **Get the facts:** endpoint, HTTP status, `error.code`, `error.requestId` (also in the `X-Request-ID` header).
2. **Known code?** Look it up in `docs/api/errors.md` (likely cause), and in the endpoint's **Errors / Diagnose** sections in `docs/api/<module>.md`.
3. **Follow the request:**

   ```bash
   docker compose logs --no-log-prefix api | grep '<request_id>' | python3 -m json.tool --json-lines
   ```

   - `request.failed`: expected business error (4xx). Check the inputs and the caller's role/membership.
   - `request.validation_failed`: `details` lists the bad fields.
   - `request.unhandled_exception`: a bug; the `exception` field has the stack trace.
   - `db.unavailable` / `db.integrity_error`: database problems.
   - No lines at all: the request never reached the API (nginx, port, network, wrong `EXPO_PUBLIC_API_BASE_URL`).
4. **Database checks:**

   ```bash
   docker compose exec api curl -s localhost:$API_PORT/health/ready
   pg_isready -h localhost -p 5432
   sudo grep chitbook /etc/postgresql/18/main/pg_hba.conf
   ```

5. **Auth problems:** check the audit trail (as the app role):

   ```sql
   SELECT created_at, event, username, details FROM auth_audit_log ORDER BY id DESC LIMIT 20;
   ```

6. **Fix with a test:**
   - Reproduce it in `apps/api/tests/integration/`, fix it, then run `uv run pytest`.
   - For live issues, rebuild (`docker compose up -d --build api`) and re-run the smoke test.
7. Runbook with more causes: `docs/operations/logging-and-debugging.md`.
