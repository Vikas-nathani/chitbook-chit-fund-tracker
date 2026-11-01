# API reference

## Where to look

| I want to… | Open |
|---|---|
| Find an endpoint | [endpoints.md](endpoints.md): every route, with its auth requirement |
| See one endpoint in full (payloads, tables, code, errors) | the module file, e.g. [simple-chits.md](simple-chits.md) |
| Understand an error code | [errors.md](errors.md) |
| See tables and columns | [../database.md](../database.md) |
| Try requests in a browser | `http://<host>:8080/api/docs` (Swagger UI, when `API_DOCS_ENABLED=true`) |

Module files: [auth](auth.md) · [users](users.md) · [simple-chits](simple-chits.md) · [groups](groups.md) ·
[funds](funds.md) · [payments](payments.md) · [ledger](ledger.md) · [auctions](auctions.md) · [loans](loans.md) ·
[reports](reports.md) · [notifications](notifications.md) · [polls](polls.md) · [media](media.md) · [chat](chat.md) ·
[health](health.md)

## Each endpoint section contains

- Method + full path, and the auth it needs
- **Router** and **Calls**: function names with `file:line` links into the code
- **Parameters**, **Request body** and **Response**: field tables and an example JSON
- **Database**: the tables written and read (recorded from the real SQL during tests)
- **Flow**: a Mermaid sequence diagram
- **Errors**: every error code the endpoint can return, and when
- **Diagnose**: the log events to search for

> Files other than this README are **generated**. Do not edit them. After changing the API, run
> `scripts/gen-docs.sh`. CI fails if the generated docs are out of date.

## Conventions

- Base path: `/api/v1`
- JSON field names: **camelCase** (`totalAmount`, `perShareAmount`)
- Times: ISO-8601 in IST, e.g. `2026-08-01T10:30:00+05:30`
- Calendar months: `yyyy-MM`, e.g. `2026-08`
- Money: JSON numbers in rupees, with 2 decimals at most
- Auth: `Authorization: Bearer <accessToken>` (see [../auth.md](../auth.md))
- Every response has an `X-Request-ID` header. You can send your own (8 to 64 characters of `A-Z a-z 0-9 . _ -`).

## Error shape

All errors use the same envelope:

```json
{
  "error": {
    "code": "CHIT_NOT_FOUND",
    "message": "Chit not found",
    "details": null,
    "requestId": "5f2c9a0d1e3b4c5d"
  }
}
```

- `code`: stable, safe to branch on in apps. The mobile app translates it (`errors.<CODE>` keys).
- `message`: English text for people. It can change at any time.
- `details`: extra data, e.g. a list of fields for `VALIDATION_ERROR`, or `retryAfterSeconds` for `AUTH_ACCOUNT_LOCKED`.
- `requestId`: search `docker compose logs api` for it.
- Every route lists the errors it can return in its router (`responses=errors(...)`); each endpoint's **Errors** table shows the HTTP status, code and the exact problem.

Validation error example:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request data is invalid",
    "details": [{ "field": "email", "message": "value is not a valid email address" }],
    "requestId": "a1b2c3d4e5f6"
  }
}
```

## Quick curl session

```bash
API=http://localhost:8080/api/v1

# 1. log in (mobile style: the refresh token comes back in the body)
TOKENS=$(curl -s -X POST $API/auth/login -H 'Content-Type: application/json' \
  -d '{"username":"vikas","password":"<password>","deviceName":"curl"}')
ACCESS=$(echo "$TOKENS" | python3 -c 'import sys,json;print(json.load(sys.stdin)["accessToken"])')

# 2. call anything
curl -s $API/simple-chits -H "Authorization: Bearer $ACCESS"

# 3. when you get AUTH_TOKEN_EXPIRED, refresh (this rotates the refresh token)
curl -s -X POST $API/auth/refresh -H 'Content-Type: application/json' -d '{"refreshToken":"<refreshToken>"}'
```
