# Security rules (always on)

- **Secrets** live only in `.env` (gitignored). `.env.example` gets placeholders like `change-me`.
- **Never** log, print or return passwords, tokens or password hashes. Response models never include `password_hash`.
- **Auth changes** (`core/security.py`, `core/deps.py`, `modules/auth/`) must keep:
  - refresh-token rotation + reuse detection
  - the session-active check on every request
  - lockout, rate limits, and generic login errors
- **Every new endpoint** decides who may call it, and has tests for "allowed" **and** "denied".
- **Never trust ids from the client** for "who is acting". Use `access.user.id`.
- **SQL:** SQLAlchemy expressions only. Never use f-strings with user input in `text()`.
- **App:** tokens stay in secure storage / memory; no AsyncStorage or localStorage for them.
