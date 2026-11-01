# ADR 0003: PostgreSQL (host instance)

- **Status:** accepted · 2026-11-01

## Decision

- Use the **PostgreSQL 18 already running on the host** (port 5432), not a container.
- ChitBook gets its own database (`chitbook`), plus `chitbook_test` for tests, and its own role, `chitbook_app`.
- The API container connects via `host.docker.internal`. `pg_hba.conf` allows only `DOCKER_SUBNET` → those databases → that role.
- Money is `NUMERIC(14,2)` and times are `timestamptz`. The role's session timezone is `Asia/Kolkata`.

## Consequences

- One Postgres to back up and monitor on this server.
- The `postgres` superuser password is used only by `scripts/setup-db.sh`, never by the app.
- `LISTEN/NOTIFY` powers live chat across API workers without extra infrastructure.
