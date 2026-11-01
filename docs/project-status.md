# Project status

_Last updated: 2026-11-01_

## Built and tested

| Area | Status | Tests |
|---|---|---|
| API foundation (config, logging, errors, request ids, security headers) | ✅ | integration |
| Auth: register, login, refresh rotation, reuse detection, lockout, rate limit, sessions, audit | ✅ | 12 integration + unit |
| Users: profile, password change (signs out other devices), delete | ✅ | integration |
| Simple chits: create, grid edits, members, payouts, escalation, stats | ✅ | 16 integration + 5 unit |
| Chit groups & memberships, join requests | ✅ | 8 integration |
| Payments, funds, ledger (+PDF), auctions, loans, reports | ✅ | 5 integration |
| Notifications, polls, media, chat (REST + WebSocket) | ✅ | integration + live smoke test |
| Mobile app: login, signup, dashboard, new chit, chit grid (month and table views), insights, settings (language, devices) | ✅ | 23 jest tests; typecheck; lint |
| Web build of the app (nginx, port 3500) | ✅ | live check |
| Docs generated from code (endpoints, tables, errors) | ✅ | `gen_api_docs.py --check` |

Totals: **API 75 tests** (unit + integration on real Postgres) · **app 23 tests** · **smoke test 16 checks** against the running stack.

## Known gaps

| Gap | Notes |
|---|---|
| App screens for chit groups, payments, auctions, loans, ledger, polls, media, chat | All of these work through the API; the app only has Simple Chits screens so far |
| Reminder sending | `notification_configs` are stored; no scheduler sends reminders yet |
| Simple chit members can't be edited or removed after creation | Only adding members is supported |
| HTTPS | Plain HTTP on 8080/3500. Put a TLS reverse proxy in front before going public (see [auth.md](auth.md#hardening-checklist-for-production)) |
| Rate-limit state is per API worker | Fine for one server; use a shared store (e.g. Redis) when scaling out |
| 2FA, biometric lock, SMS OTP, Google/Apple sign-in | Not in scope for now |
| iOS store build | Needs an Apple Developer account for `eas build -p ios` |

## Next steps (suggested)

1. App screens for chit groups (join by code, members, payments).
2. Edit and remove simple-chit members.
3. A reminder scheduler that uses `notification_configs`.
4. HTTPS reverse proxy plus the production `.env` (`REFRESH_COOKIE_SECURE=true`, `API_DOCS_ENABLED=false`).
