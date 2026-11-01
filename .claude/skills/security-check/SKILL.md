---
name: security-check
description: Review the current ChitBook changes for security problems - auth/session handling, access control on every endpoint, secrets, injection, logging of sensitive data, token storage in the app. Use before committing auth-related or new-endpoint changes, or when asked for a security review.
---

# Security check

Run `git diff` (and `git diff --staged`), then check each item. Report findings as file:line + risk + fix.

## API

- [ ] Every new or changed endpoint has an access check in its service (`Access.*`), with a test for the denied caller.
- [ ] No "acting user" ids are taken from the request body; `access.user.id` is used.
- [ ] Owner-scoped lookups filter by owner (`*_NOT_FOUND` for others).
- [ ] No `text()` / raw SQL built from user input.
- [ ] Auth code still has:
  - rotation + reuse detection (`auth/service.refresh`)
  - the session-active check (`core/deps.authenticate_token`)
  - lockout, rate limits, generic login errors
- [ ] Response models don't expose `password_hash`, tokens or internal fields.
- [ ] Logs don't contain passwords, tokens or personal data (keys in `SENSITIVE_KEYS` are redacted; check new key names).
- [ ] New settings come from `.env` without defaults. Secrets are not in code, compose files or docs.
- [ ] Input limits (`Field(max_length=..., ge=..., le=...)`) on new request fields.

## App

- [ ] Tokens only in `tokenStore` / `api/client.ts`. No AsyncStorage, localStorage or logging of them.
- [ ] No secrets in `EXPO_PUBLIC_*` variables (they ship inside the app).
- [ ] User input is validated before sending; API errors are shown via `tError`.

## Deployment

- [ ] `.env` is not staged (`git status`).
- [ ] Production: HTTPS proxy, `REFRESH_COOKIE_SECURE=true`, `API_DOCS_ENABLED=false`, 8080 not public.

Finish by running `cd apps/api && uv run pytest`.
