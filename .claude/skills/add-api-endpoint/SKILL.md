---
name: add-api-endpoint
description: Add or change a ChitBook API endpoint (FastAPI) end to end - schema, service rule + access check, router, error codes, logs, migration if needed, tests, generated docs and app types. Use for any new route or change to a request/response.
---

# Add an API endpoint

Follow these steps in order. Copy patterns from `apps/api/src/chitbook_api/modules/auctions/` (small) or `simple_chits/` (rich).

1. **Decide the contract.**
   - Method + path under the module prefix: plural nouns, `{id}` path params, camelCase query aliases.
   - Who may call it: public / signed in / self / group member / group admin / platform admin.
   - Success status: 200 read/update, 201 create, 204 delete.
2. **Schemas** (`schemas.py`):
   - Request model extends `ApiModel`, with `Field(...)` limits.
   - Response model uses `Money` and `AppDateTime`.
3. **Model / migration** (only if the data shape changes): edit `models.py`, then follow `/db-migration`.
4. **Repository** (`repository.py`): only queries; return models.
5. **Service** (`service.py`):
   - The access check comes first (`await access.require_group_admin(group_id)` etc.).
   - Rules raise `AppError(ErrorCode.X)`. Add new codes to `core/errors.py` as `(HTTP status, message, exact problem / fix)`.
   - In the router, list every error the route can return: `responses=errors(*AUTHED, ErrorCode.VALIDATION_ERROR, ErrorCode.X)`. `scripts/gen-docs.sh` fails and names the route if the list is incomplete or has extras.
   - `log.info("<module>.<event>", ids...)` after the change succeeds.
   - Use `flush()` + `refresh()` when you need ids or defaults. Never `commit()`.
6. **Router** (`router.py`): one function that calls one service function, with `response_model`, `status_code` and `summary`.
7. **Register the router** in `main.py`, if it's a new module.
8. **Tests** (`tests/integration/test_<module>.py`):
   - Happy path.
   - Every error code you added.
   - Denied access: an outsider, a non-admin.
   - Assert on `error.code`.
9. **Verify:**

   ```bash
   cd apps/api && uv run pytest && uv run ruff check . && uv run ruff format --check . && uv run mypy
   ```

10. **Docs and app types:**
    - `scripts/gen-docs.sh`
    - If the app uses the endpoint: rebuild the API (`docker compose up -d --build api`), then run `scripts/gen-api-types.sh`.
11. **User-visible error code:** add `errors.<CODE>` to `apps/mobile/src/i18n/en.ts` **and** `te.ts`.
