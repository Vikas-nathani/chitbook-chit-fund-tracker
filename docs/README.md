# ChitBook documentation

| Start here | |
|---|---|
| [setup.md](setup.md) | install, `.env`, database, run, everyday commands |
| [architecture.md](architecture.md) | system diagram, folder layout, life of a request |
| [project-status.md](project-status.md) | what's built, what's missing |

| Reference | |
|---|---|
| [api/README.md](api/README.md) | API conventions, error shape, links to every module |
| [api/endpoints.md](api/endpoints.md) | all endpoints *(generated)* |
| [api/errors.md](api/errors.md) | all error codes *(generated)* |
| [database.md](database.md) | ER diagram, every table and column *(generated)* |
| [auth.md](auth.md) | login, tokens, sessions, roles, hardening |
| [mobile.md](mobile.md) | app screens, data flow, builds |

| Business rules | |
|---|---|
| [domain/simple-chits.md](domain/simple-chits.md) | shares, late joiners, escalation, worked example |
| [domain/chit-groups.md](domain/chit-groups.md) | groups, payments, loans, auctions, ledger, reports |

| Operations | |
|---|---|
| [operations/logging-and-debugging.md](operations/logging-and-debugging.md) | log format, following a request, fixing 500/503 |
| [adr/](adr/) | why we chose FastAPI, Expo, Postgres, JWT rotation |

**Generated files:** `api/*.md` (except `api/README.md`) and `database.md` come from the code. Run `scripts/gen-docs.sh` after changing the API; CI fails if they're stale.
