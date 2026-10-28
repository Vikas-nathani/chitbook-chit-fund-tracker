# ChitBook — Project Status

This file tracks what's been built, what's been tested, and what's still open, so anyone
picking up this repo (including a future AI session) can get oriented quickly.

## What ChitBook is

A chit fund tracker: Spring Boot backend (Java 21) + React/Vite frontend, MySQL storage,
Docker Compose for local/dev deployment, and a Capacitor-wrapped Android build of the
frontend for installing on a phone. See `AGENTS.md` for the full backend architecture guide.

## Current deployment

Running via `docker compose up --build -d` on this VM (`34.14.197.155`):
- `app` (Spring Boot) — host port `8080`
- `web` (nginx + built React app) — host port `3500`
- `db` (MySQL 8) — host port `3307`, bound to the host for local dev convenience

Admin login: username `vikas`, see `.env` for the password (gitignored, not in this repo).

## Android app

The `frontend/` React app is wrapped with Capacitor (`frontend/capacitor.config.ts`,
`frontend/android/`) to produce an installable `.apk`:
- `androidScheme: 'http'` is set deliberately — the API is plain HTTP, and Capacitor's
  default `https://localhost` scheme for the app's own pages would trigger Android's
  mixed-content blocking against an HTTP API. Keeping both on `http` avoids that.
- The debug APK points at `http://34.14.197.155:8080` (`VITE_API_BASE_URL` at build time,
  see `frontend/src/api.ts`'s `API_BASE`). Rebuild with:
  ```
  cd frontend
  VITE_API_BASE_URL=http://34.14.197.155:8080 npm run build
  npx cap sync android
  cd android && ANDROID_HOME=/home/dev/android-sdk JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 ./gradlew assembleDebug
  ```
  Output: `frontend/android/app/build/outputs/apk/debug/app-debug.apk`.
- **Known gap**: traffic is plain HTTP over a public IP with HTTP Basic auth — fine for
  personal testing, not production-secure. A security hardening pass (HTTPS, closing
  public port 8080 behind a reverse proxy, rate limiting, locking down public
  registration) was scoped but **not done yet** — deliberately dropped mid-session in
  favor of the Simple Chits feature work below, at the user's request.

## Simple Chits — feature redesign (this session's main work)

The "Simple Chits" module (`src/main/java/com/nival/chit/{entity,services,controllers,dto}/SimpleChit*`,
`frontend/src/pages/{NewChit,ChitGrid}.tsx`) was redesigned to match how the owner actually
runs chits, replacing the old flat "equal split across however many names were typed" model.

### What changed

1. **One common per-share amount, not an auto-divide.** `SimpleChit.perShareAmount` is a
   single value for the whole chit (suggested as `totalAmount ÷ months`, editable), set once
   at creation. Previously the backend silently computed `totalAmount ÷ memberCount`, which
   broke the moment the member count didn't match the chit's intended slot count.
2. **Shares, not duplicate name rows.** `SimpleChitMember.shares` (default 1) lets one person
   hold multiple slots without retyping their name — their monthly entry is
   `chit.perShareAmount × member.shares`.
3. **Add members after creation.** New endpoint `POST /api/chit/simple-chits/{id}/members`
   (`SimpleChitService.addMember`). Deliberately **add-only** in this pass — editing or
   removing an existing member's shares/amount/join-month is still a gap.
4. **Late joiners.** `SimpleChitMember.startMonthIndex` — a member's `SimpleChitEntry` rows
   only exist from their own start month onward; earlier months simply have no entry (not a
   zero placeholder), so due/collected totals for those months naturally exclude them.
   `SimpleChitMath` already summed by iterating existing entries, so no month-math changes
   were needed there.
5. **Payout escalation.** Per-chit toggle `SimpleChit.escalationEnabled` + `escalationPercent`
   (default 1%). When a payout is recorded, the *taking member's own* remaining months go up
   by `totalAmount × escalationPercent / 100`; the exact bump is stored on
   `SimpleChitPayout.escalationApplied` so deleting or replacing that payout reverses it
   precisely rather than recomputing (see `SimpleChitService.savePayout`/`deletePayout`).
6. **Mobile-first grid UI.** `ChitGrid.tsx` now defaults to a month-by-month card view (one
   month at a time, big tap targets, Prev/Next navigation) instead of the old one-big-table
   layout, which was confirmed via screenshot to be unusable on a phone. The full table is
   still available via a "Table view" toggle for wider screens.

### Files touched

- Backend: `entity/SimpleChit.java`, `SimpleChitMember.java`, `SimpleChitPayout.java`;
  `dto/CreateSimpleChitDTO.java`, `UpdateSimpleChitDTO.java`, `SimpleChitDTO.java`, and new
  `dto/AddSimpleChitMemberDTO.java`; `services/SimpleChitService.java`;
  `controllers/SimpleChitController.java`.
- Frontend: `src/api.ts` (new types/fields, `api.addMember`), `src/pages/NewChit.tsx`
  (per-member rows: name/shares/join-month, chit-level per-share amount field, escalation
  toggle), `src/pages/ChitGrid.tsx` (month-card view, table view toggle, add-member modal,
  escalation preview in the payout modal), `src/styles.css` / `src/pnl.css` (new classes),
  `src/i18n/en.ts` + `te.ts` (new keys, English and Telugu).

### Known gaps / deliberately out of scope

- No editing or removing an existing member after creation (add-only).
- No UI for toggling escalation after the chit is created (only at creation time via the
  form) — `UpdateSimpleChitDTO` supports it server-side, just no frontend control yet.
- `spring.jpa.hibernate.ddl-auto=update` is still in use (not Flyway) — the schema changes
  above were applied automatically on container restart; two pre-existing test chits in the
  dev database got `per_share_amount=0` from the migration and were manually backfilled
  (`UPDATE simple_chit SET per_share_amount = ROUND(total_amount / months, 2) WHERE
  per_share_amount = 0`) — worth remembering if you see similar zero-value columns after a
  future schema change on a non-empty table.

## Testing

### Backend
`src/test/java/com/nival/chit/services/SimpleChitServiceTest.java` — JUnit 5 + Mockito, no
DB required. Covers: shares multiplier, late-join sparse entries, add-member isolation
(doesn't touch other members), owner-scoping rejection, escalation apply/reverse/replace.
Run: `./mvnw test -Dtest=SimpleChitServiceTest`. The pre-existing `ChitApplicationTests`
smoke test needs a live DB on `localhost:3306` and will fail outside Docker — that's expected
and unrelated to this work.

### Frontend
Vitest + React Testing Library, newly set up (`frontend/vitest.config.ts`,
`frontend/src/test/setup.ts`, `frontend/src/test/renderWithProviders.tsx`).
`src/pages/NewChit.test.tsx` and `src/pages/ChitGrid.test.tsx` cover the member-row
add/shares flow, the shares badge, the escalation toggle, month-view visibility by join
date, and the add-member modal payload. Run: `npm run test` (from `frontend/`).

### End-to-end (verified manually against the live Docker stack this session)
Created a chit with mixed shares + a late joiner via the API, confirmed late-joiner months
are `null` before their start month, added a member post-creation, recorded a payout with
escalation on and confirmed the exact bump landed only on that member's future months,
deleted the payout and confirmed the bump reversed exactly, then cleaned up the test chit.

## Next steps (not started)

- Production security hardening pass (was scoped in detail, then paused): admin-approval
  gating for public registration, TLS (self-signed cert was the agreed approach), rate
  limiting / brute-force protection on login & registration, CORS origin lock-down,
  Swagger UI disablement in non-dev, account-status enforcement in `CustomUserDetailsService`.
- Rebuilding the Android APK with the new Simple Chits UI (the APK currently installed on
  the phone predates this feature work).
