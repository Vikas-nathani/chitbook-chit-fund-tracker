# ADR 0004: JWT access tokens + rotating refresh tokens

- **Status:** accepted · 2026-11-01

## Context

- Phones need long sign-ins without storing passwords.
- Stolen tokens must be detectable and revocable.

## Decision

- **Access token:** a 15-minute JWT, held in memory only.
- **Refresh token:**
  - 30 days, opaque, stored hashed in the database.
  - Rotated on every use. Reusing an old one revokes the whole session family.
- **Revocation:** every request checks that the token's session is still active, so logout and remote sign-out take effect immediately.
- **Where the refresh token lives:**
  - Phones: Keychain / Keystore.
  - Web: an `HttpOnly SameSite=Strict` cookie, plus a custom header on refresh. No browser storage.
- **Login protection:** Argon2id hashing, account lockout with backoff, a per-IP rate limit, and an audit log.

## Consequences

- One extra indexed query per request (the session check). This is the price of instant revocation.
- Clients must refresh one at a time (single flight). The app's API client does this.
- 2FA, biometrics and social login can be added later on top of this design.
