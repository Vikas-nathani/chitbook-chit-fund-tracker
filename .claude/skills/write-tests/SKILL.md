---
name: write-tests
description: Write or extend tests for ChitBook - API integration tests on real Postgres, API unit tests, app unit tests and screen tests. Use when adding behaviour, fixing a bug, or when coverage is missing.
---

# Write tests

## API (`apps/api/tests`)

| Kind | Where | When |
|---|---|---|
| unit | `tests/unit/` | pure logic (math, time, security helpers); no DB |
| integration | `tests/integration/test_<module>.py` | endpoints through HTTP on the real `chitbook_test` DB |

Fixtures (`tests/conftest.py`, `tests/integration/conftest.py`):

- `client`: httpx client for the app
- `make_user("ravi")`: returns `{"user", "headers", "tokens", "password"}`
- `admin_headers`: the platform admin
- `group_setup`: `lead` (group admin), `member` (active), `outsider`, and `group`

Pattern:

```python
async def test_member_cannot_delete_group(client, group_setup):
    r = await client.delete(f"/api/v1/groups/{group_setup['group']['id']}", headers=group_setup["member"]["headers"])
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "NOT_GROUP_ADMIN"
```

- Cover the happy path, every error code, allowed **and** denied callers, and money with exact numbers.
- Run: `cd apps/api && uv run pytest -q`. Every test starts with empty tables plus the admin.

## App (`apps/mobile`)

- **Pure logic:** `*.test.ts` next to the file, e.g. `features/chits/gridDraft.test.ts`. Use `src/test/fixtures.ts`.
- **Screens:** `src/test/screens/*.test.tsx` (never under `src/app/`).
  - `jest.mock('expo-router', ...)`, `jest.mock('@/api/endpoints', ...)`.
  - `await renderWithProviders(<Screen />)`; `await fireEvent.changeText/press(...)`.
  - Query by `getByLabelText` / `getByText`, which also checks accessibility labels.
- Run: `npm test`.
