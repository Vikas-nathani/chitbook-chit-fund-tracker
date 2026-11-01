# ChitBook

Chit fund tracker made of a **Python FastAPI API** (`apps/api`) and a **React Native + Expo app** (`apps/mobile`) for Android, iOS and web. It uses the **host PostgreSQL 18** on port 5432.

Read [docs/README.md](docs/README.md) for everything else. Key docs: [architecture](docs/architecture.md) · [setup](docs/setup.md) · [API](docs/api/README.md) · [auth](docs/auth.md) · [simple-chit rules](docs/domain/simple-chits.md) · [debugging](docs/operations/logging-and-debugging.md)

## Non-negotiable rules

1. **Config comes only from `.env`.**
   - No default values in code, compose files, Dockerfiles or nginx config. Every setting is a required variable.
   - When you add one, update `.env`, `.env.example`, `core/config.py` and the table in `docs/setup.md`.
2. **IST everywhere.**
   - `TZ=Asia/Kolkata`. Store `timestamptz`, and return ISO times with `+05:30`.
   - Use `core/time.py` (`now()`, `today()`, `YearMonth`), never `datetime.now()` or `date.today()`.
3. **Money is `Decimal` / `NUMERIC(14,2)`** in the API. Round half-up to paise.
4. **Errors:**
   - Raise `AppError(ErrorCode.X)`. If you add a code, add it in `core/errors.py` (HTTP status, message, exact problem) **and** in the app's `en.ts`/`te.ts` (`errors.X`) when users can see it.
   - Every route lists its errors in the router: `responses=errors(*AUTHED, ErrorCode.X, ...)`. `scripts/gen-docs.sh` fails if the list doesn't match the code.
   - Never return bare strings.
5. **Logging:**
   - `structlog` events named `module.action` (e.g. `simple_chit.payout_saved`), with ids as fields.
   - Never log passwords, tokens or personal data.
6. **Access checks** live in the service layer, using `Access` (`core/deps.py`). Every new endpoint needs one.
7. **Docs describe the current system only.** Use bullets, examples and Mermaid diagrams, with no long paragraphs and no "previously…". After any API change run `scripts/gen-docs.sh`.
8. **Tests:** every behaviour change comes with a test. API tests run against real Postgres (`chitbook_test`).
9. **Files:** create files with Write and change them with Edit, so the user can see the diffs. Don't use shell heredocs or sed.

## Commands

| Task | Command |
|---|---|
| Run the stack | `docker compose up -d --build` (api :8080, web :3500) |
| API tests | `cd apps/api && uv run pytest` |
| API lint/types | `cd apps/api && uv run ruff check . && uv run ruff format --check . && uv run mypy` |
| App tests/types/lint | `cd apps/mobile && npm test && npm run typecheck && npm run lint` |
| Regenerate docs | `scripts/gen-docs.sh` · check: `apps/api/.venv/bin/python scripts/gen_api_docs.py --check` |
| Regenerate app API types | `scripts/gen-api-types.sh` (API running) |
| Smoke test the live stack | `apps/api/.venv/bin/python scripts/smoke_test.py` |
| Logs | `docker compose logs -f api` (JSON on stdout, search by `request_id`; no log files) |

- Tools live at `~/.local/bin` (uv) and `~/.local/node/bin` (node). Add both to `PATH` if a command is missing.

## Layout

```
apps/api/src/chitbook_api/{core,modules/<feature>/{models,schemas,repository,service,router}.py}
apps/api/{migrations,tests/{unit,integration}}
apps/mobile/src/{app (routes), features, components, api, auth, i18n, lib, theme, test}
docs/  scripts/  infra/{nginx,postgres}  .claude/{rules,skills,agents,hooks}
```

## Workflows (skills in `.claude/skills/`)

- `/add-api-endpoint` · `/add-mobile-screen` · `/db-migration` · `/write-tests`
- `/run-stack` · `/debug-api-error` · `/update-api-docs` · `/security-check`
- `/deploy` · `/release-mobile`

## Done means

- All tests, lint and typechecks pass (API **and** app, if both were touched).
- `scripts/gen-docs.sh` has been run if the API changed, and `docs/project-status.md` is updated if a feature or gap changed.
- For anything user-visible, the stack has been checked running (`/run-stack`, smoke test).
