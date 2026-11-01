# Architecture

## System at a glance

```mermaid
flowchart LR
    subgraph Phones
        A[Android app]
        I[iOS app]
    end
    B[Browser]
    subgraph Docker["Docker (network chitbook_net 172.29.0.0/24)"]
        W["web: nginx + Expo web build<br/>:3500"]
        API["api: FastAPI (uvicorn, 2 workers)<br/>:8080"]
    end
    PG[("Host PostgreSQL 18<br/>:5432 · db chitbook")]
    A -- HTTPS/HTTP JSON --> API
    I -- HTTPS/HTTP JSON --> API
    B --> W
    W -- "/api/* (+ WebSocket)" --> API
    API -- "asyncpg, role chitbook_app" --> PG
    API -. "LISTEN/NOTIFY chat_messages" .- PG
```

- **Phones** call the API directly, at `EXPO_PUBLIC_API_BASE_URL`.
- **Browsers** load the web build from nginx. nginx proxies `/api` to the API, so everything is one origin and no CORS is needed.
- **Database:** the Postgres already installed on the host. The API container reaches it at `host.docker.internal:5432`.
- **Live chat:** messages are fanned out with Postgres `LISTEN/NOTIFY`, so every API worker can push them to its WebSocket clients.

## Repository layout

```
chitbook/
├── apps/
│   ├── api/                 Python FastAPI backend
│   │   ├── src/chitbook_api/
│   │   │   ├── main.py      app factory: middleware, error handlers, routers
│   │   │   ├── core/        config, db, security, deps (auth + access), errors, logging, middleware
│   │   │   └── modules/     one folder per feature (see below)
│   │   ├── migrations/      Alembic (database schema history)
│   │   └── tests/           unit/ (pure logic) + integration/ (HTTP + real Postgres)
│   └── mobile/              Expo (React Native) app: Android, iOS, web
│       └── src/
│           ├── app/         screens (expo-router: file = route)
│           ├── features/    feature logic + components (chits, insights)
│           ├── components/  shared UI kit
│           ├── api/         HTTP client, endpoints, generated types
│           ├── auth/        session provider
│           ├── i18n/        English + Telugu
│           └── lib/, theme/
├── infra/                   nginx template, Postgres setup SQL
├── scripts/                 setup-db, gen-api-types, gen-docs, smoke test
├── docs/                    this documentation
├── .claude/                 Claude Code project setup (rules, skills, agents, hooks)
└── docker-compose.yml
```

## Backend module pattern

Every feature folder in `apps/api/src/chitbook_api/modules/<feature>/` has the same files:

| File | Job | Example |
|---|---|---|
| `models.py` | SQLAlchemy tables | `SimpleChit`, `SimpleChitMember` |
| `schemas.py` | Pydantic request/response bodies (camelCase JSON) | `SimpleChitCreate`, `SimpleChitOut` |
| `repository.py` | Database queries, no rules | `get_owned(session, chit_id, owner_id)` |
| `service.py` | Business rules and access checks; raises `AppError` | `save_payout(...)` |
| `router.py` | HTTP layer only: parse → call service → return | `PUT /simple-chits/{id}/payouts/{month}` |

Modules: `auth`, `users`, `simple_chits`, `groups`, `funds`, `payments`, `ledger`, `auctions`, `loans`,
`reports`, `notifications`, `polls`, `media`, `chat`, `health`.

## Life of a request

```mermaid
sequenceDiagram
    participant C as Client
    participant M as RequestContextMiddleware
    participant CORS as CORSMiddleware
    participant R as router function
    participant D as deps (session, current user, Access)
    participant S as service
    participant DB as Postgres
    C->>M: HTTP request
    M->>M: request_id = X-Request-ID or new uuid
    M->>CORS: pass on
    CORS->>R: matched route
    R->>D: open DB session, verify JWT, check session not revoked
    D->>DB: SELECT auth_sessions, users
    R->>S: call use case
    S->>DB: queries via repository
    S-->>R: result or AppError(code)
    R-->>D: endpoint returns → COMMIT (before the response is sent)
    R-->>M: JSON response / error envelope
    M->>M: log "http.request" (status, duration_ms, user_id)
    M-->>C: response + X-Request-ID + security headers
```

- **Commit timing:** the transaction commits **before** the response is sent (`Depends(get_session, scope="function")`). A client that sends a follow-up request immediately always sees the committed data.
- **Known errors:** any `AppError` becomes the standard error envelope, with its HTTP status.
- **Unexpected errors:** the middleware catches them, logs the stack trace with the request id, and returns `INTERNAL_ERROR`.

## Mobile app structure

```mermaid
flowchart TD
    Layout["app/_layout.tsx<br/>providers + Stack.Protected"] --> Auth["login · signup"]
    Layout --> Tabs["(tabs): Chits · Insights · Settings"]
    Layout --> New["chits/new"]
    Layout --> Detail["chits/[id]"]
    Detail --> MonthView & TableView & Sheets
    Tabs & New & Detail --> Hooks["features/chits/hooks.ts<br/>TanStack Query"]
    Hooks --> Client["api/client.ts<br/>Bearer token + auto refresh"]
    Client --> Store["lib/tokenStore<br/>Keychain/Keystore (phones) · HttpOnly cookie (web)"]
```

## Key technology choices

| Area | Choice | Why (see [adr/](adr/)) |
|---|---|---|
| API | FastAPI + SQLAlchemy 2 (async) + Alembic | typed, fast, auto OpenAPI, mature migrations |
| DB | PostgreSQL | strong typing (NUMERIC money, timestamptz), LISTEN/NOTIFY |
| Auth | JWT access + rotating refresh tokens | stateless checks, revocable sessions, theft detection |
| App | React Native + Expo | one TypeScript codebase for Android, iOS and web; cloud builds |
| Logs | structlog JSON | one line per event, searchable by request_id |
