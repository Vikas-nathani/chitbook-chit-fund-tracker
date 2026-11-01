# Setup & running

## What you need

| Tool | Version | Used for |
|---|---|---|
| Docker + Compose | 24+ | running the API and web app |
| PostgreSQL | 18 (on the host, port 5432) | the database |
| uv | latest (`curl -LsSf https://astral.sh/uv/install.sh \| sh`) | Python tooling for API dev/tests |
| Node.js | 22 LTS | the mobile app |
| Expo Go app (phone) | from the Play Store / App Store | trying the app on a phone |

## 1. Configure `.env`

```bash
cp .env.example .env    # then fill in every value; there are no defaults
```

| Variable | Example | Meaning |
|---|---|---|
| `TZ` | `Asia/Kolkata` | timezone for the API, the containers and DB sessions |
| `DOCKER_SUBNET` | `172.29.0.0/24` | compose network; allowed in `pg_hba.conf` |
| `POSTGRES_SUPERUSER(_PASSWORD)` | `postgres` / … | used **only** by `scripts/setup-db.sh` |
| `POSTGRES_SETUP_HOST` | `localhost` | where setup-db connects |
| `DB_HOST` | `host.docker.internal` | how the API container reaches the host Postgres |
| `DB_PORT` / `DB_NAME` / `DB_TEST_NAME` | `5432` / `chitbook` / `chitbook_test` | |
| `DB_USER` / `DB_PASSWORD` | `chitbook_app` / random | the app's own least-privilege role |
| `DB_POOL_SIZE` / `DB_POOL_MAX_OVERFLOW` | `10` / `5` | connections per worker |
| `API_PORT` / `API_WORKERS` | `8080` / `2` | |
| `API_DOCS_ENABLED` | `true` | Swagger at `/api/docs` |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:3500,…` | comma-separated browser origins |
| `FORWARDED_ALLOW_IPS` | `172.29.0.0/24` | trust `X-Forwarded-For` only from nginx |
| `JWT_SECRET` / `JWT_ISSUER` | random 64+ chars / `chitbook-api` | signing access tokens |
| `ACCESS_TOKEN_TTL_MINUTES` / `REFRESH_TOKEN_TTL_DAYS` | `15` / `30` | |
| `REFRESH_COOKIE_SECURE` | `false` (dev) / `true` (HTTPS) | web refresh cookie flag |
| `LOGIN_MAX_FAILED_ATTEMPTS` / `LOGIN_LOCKOUT_BASE_MINUTES` / `LOGIN_LOCKOUT_MAX_MINUTES` | `5` / `5` / `1440` | lockout |
| `RATE_LIMIT_AUTH_PER_MINUTE` | `10` | per IP on login, register and refresh |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` / `ADMIN_NAME` / `ADMIN_EMAIL` | | platform admin created at startup if missing |
| `LOG_LEVEL` | `INFO` | API log level (logs go to stdout only) |
| `LOG_MAX_SIZE` / `LOG_MAX_FILES` | `10m` / `5` | Docker rotates the api container's stdout log at this size, keeping this many files |
| `WEB_PORT` / `API_UPSTREAM` | `3500` / `api` | nginx |
| `EXPO_PUBLIC_API_BASE_URL` | `http://<server-ip>:8080` | API address baked into phone builds |

Generate secrets:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"   # JWT_SECRET
python3 -c "import secrets; print(secrets.token_urlsafe(24))"   # DB_PASSWORD
```

## 2. Prepare the database (once)

```bash
scripts/setup-db.sh
```

It:

- creates the role `chitbook_app` and the databases `chitbook` and `chitbook_test` (owned by that role)
- sets the role's timezone to `TZ`
- adds two lines to `pg_hba.conf` (via sudo) allowing `DOCKER_SUBNET` to reach only those databases as that role, then reloads Postgres
- finishes by testing a login as the app role

It's safe to run again; it also re-syncs the role's password with `.env`.

## 3. Run everything

```bash
docker compose up -d --build        # api on :8080, web on :3500
docker compose ps                   # both should be "healthy"/"Up"
curl localhost:8080/health/ready    # {"status":"ok",...,"database":"ok (timezone=Asia/Kolkata)"}
```

- The API container applies migrations (`alembic upgrade head`) every time it starts.
- Logs: `docker compose logs -f api` (JSON lines; no log files in the repo).
- Web app: `http://<host>:3500`. Swagger: `http://<host>:8080/api/docs`.

## 4. Mobile app on a phone

```bash
cd apps/mobile
npm install
EXPO_PUBLIC_API_BASE_URL=http://<server-ip>:8080 npx expo start
```

- Scan the QR code with **Expo Go** (Android) or the Camera app (iOS).
- The phone must be able to reach `<server-ip>:8080`.

Store builds (EAS, in the cloud; no Mac needed):

```bash
npx eas-cli@latest login
npx eas-cli@latest build -p android --profile preview   # installable APK
npx eas-cli@latest build -p ios                          # needs an Apple Developer account
```

## Everyday commands

| Task | Command |
|---|---|
| Start / stop | `docker compose up -d --build` · `docker compose down` |
| API logs | `docker compose logs -f api` · one request: `docker compose logs api \| grep <requestId>` |
| API tests | `cd apps/api && uv run pytest` |
| API lint + types | `cd apps/api && uv run ruff check . && uv run ruff format --check . && uv run mypy` |
| New DB migration | `cd apps/api && DB_HOST=localhost uv run --env-file ../../.env alembic revision --autogenerate -m "what changed"` |
| Apply migrations locally | `cd apps/api && DB_HOST=localhost uv run --env-file ../../.env alembic upgrade head` |
| App tests / types / lint | `cd apps/mobile && npm test && npm run typecheck && npm run lint` |
| Regenerate app API types | `scripts/gen-api-types.sh` (API must be running) |
| Regenerate API docs | `scripts/gen-docs.sh` |
| End-to-end smoke test | `apps/api/.venv/bin/python scripts/smoke_test.py` |
