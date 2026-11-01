# ChitBook app (Expo SDK 58 · React Native 0.88 · expo-router)

@AGENTS.md

## Project rules

- **Screens** live in `src/app/` (file = route). Everything else goes outside it: `src/features/<feature>/` for feature logic and components, `src/components/ui` for the shared kit.
- **Server data:** only through hooks in `src/features/*/hooks.ts` (TanStack Query). Screens never call `api` directly.
- **API types:** come from `src/api/schema.d.ts`, which is generated. Never edit it; run `scripts/gen-api-types.sh`. Add friendly aliases in `src/api/types.ts`.
- **Text:**
  - Every user-visible string goes through `t()` / `tn()`.
  - Add each key to **both** `src/i18n/en.ts` and `te.ts`; a test enforces this.
  - Show API errors with `tError(err)`, which maps by `error.code`.
- **Tokens:**
  - Never put tokens in AsyncStorage or localStorage. `src/lib/tokenStore.ts` (secure store) and `tokenStore.web.ts` (HttpOnly cookie) are the only places.
  - The access token stays in memory (`src/api/client.ts`).
- **Styling:** use `src/theme` tokens and `src/components/ui`. Touch targets are at least `TOUCH` (48).
- **Rules logic:** money and grid rules are pure functions in `src/features/chits/gridDraft.ts`, with unit tests. Keep them in step with the API rules in `docs/domain/simple-chits.md`.
- **Tests:** go in `*.test.ts(x)` next to the code, or in `src/test/screens/` for screens (never inside `src/app/`). Use `await renderWithProviders(...)` and `await fireEvent...` (RNTL v14 is async).
- **Effects:** no `setState` directly inside `useEffect`; the React Compiler lint rule rejects it. Derive values instead, or remount with `key`.

## Commands (from `apps/mobile`)

```bash
npm test                 # jest (jest-expo)
npm run typecheck        # tsc --noEmit
npm run lint             # expo lint
EXPO_PUBLIC_API_BASE_URL=http://<server-ip>:8080 npx expo start
npx expo export --platform web      # what the web container builds
npx expo-doctor
```
