---
paths:
  - "apps/mobile/**/*.{ts,tsx}"
---

# App (TypeScript) rules

- **Expo SDK 58.** Check versioned docs (`https://docs.expo.dev/versions/v58.0.0/`) before using any Expo/RN API. Add packages with `npx expo install`.
- **Routes** only in `src/app/`. Tests and helpers never go inside it.
- **Server state:** feature hooks (`src/features/*/hooks.ts`) with TanStack Query keys from `chitKeys`-style factories.
- **Strings:** `t('key')` with the key added to both `en.ts` and `te.ts`. API errors go through `tError(err)`.
- **Security:** no tokens outside `tokenStore` / `api/client.ts`. No `console.log` of user data.
- **UI:** `src/components/ui` + `src/theme` tokens. Add `accessibilityRole`/`accessibilityLabel` on every touchable. Touch targets ≥ 48.
- **Strict TypeScript** with `noUncheckedIndexedAccess`; handle `undefined` from indexing.
- **No `setState` directly in effects.** Derive values, or remount with `key`.
