---
name: update-api-docs
description: Regenerate and verify ChitBook's generated documentation (docs/api/*.md, docs/database.md) after API, schema, model, error-code or log-event changes, and update hand-written docs that the change affects.
---

# Update API docs

1. Regenerate. This runs the tests with SQL tracing, then builds the markdown:

   ```bash
   scripts/gen-docs.sh
   apps/api/.venv/bin/python scripts/gen_api_docs.py --check   # must print nothing and exit 0
   ```

2. Read the diff of `docs/api/<module>.md` for the changed endpoints:
   - The **Database** lines are right. If it says "no SQL recorded", add a test that calls the endpoint.
   - The **Errors** table lists the new codes. Add a cause for each new code to `CAUSES` in `scripts/gen_api_docs.py`.
   - Example JSON looks sensible. Improve the field-name samples in `example_for()` if not.
3. Update the hand-written docs that describe the behaviour, following `.claude/rules/docs.md`:
   - business rules → `docs/domain/*.md`
   - auth → `docs/auth.md`
   - screens → `docs/mobile.md`
   - new settings → the `.env` table in `docs/setup.md`
   - features or gaps → `docs/project-status.md` (update the date)
4. Never hand-edit generated files. A hook blocks it.
