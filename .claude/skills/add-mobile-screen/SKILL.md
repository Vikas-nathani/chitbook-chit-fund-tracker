---
name: add-mobile-screen
description: Add or change a screen in the ChitBook Expo app (Android/iOS/web) - route file, feature hooks, UI kit, English + Telugu text, tests, typecheck/lint. Use for any new screen, tab, sheet or app flow.
---

# Add a mobile screen

1. **Check the Expo SDK 58 docs** for any Expo/RN API you'll use (`https://docs.expo.dev/versions/v58.0.0/`). Add packages only with `npx expo install <pkg>`.
2. **Route:** create `apps/mobile/src/app/<path>.tsx` with a default export.
   - Signed-in screens: register in `src/app/_layout.tsx` inside `Stack.Protected guard={signedIn}`, or add a tab in `src/app/(tabs)/_layout.tsx`.
3. **Data:** add query/mutation hooks in `src/features/<feature>/hooks.ts`, with a key factory like `chitKeys`.
   - Mutations update or invalidate the related queries.
   - Endpoint functions go in `src/api/endpoints.ts`; type aliases in `src/api/types.ts`.
   - If the API types are missing, run `scripts/gen-api-types.sh`.
4. **UI:** compose from `src/components/ui` (`Screen`, `Card`, `Field`, `Button`, `Sheet`, `StatTile`, …) and `src/theme`.
   - Larger pieces go in `src/features/<feature>/`.
   - Every touchable needs `accessibilityRole` and `accessibilityLabel`.
5. **Text:** add keys to `src/i18n/en.ts` **and** `te.ts`. Use `t()`, `tn()`, and `tError(err)` for API errors.
6. **Logic:** put money/rules calculations in pure functions with unit tests (see `features/chits/gridDraft.ts`).
7. **Tests:** add `src/test/screens/<Screen>.test.tsx`.
   - Mock `expo-router` and `@/api/endpoints`.
   - `await renderWithProviders(<Screen />)`; `await fireEvent.press(...)`.
8. **Verify** (from `apps/mobile`):

   ```bash
   npm test && npm run typecheck && npm run lint && npx expo export --platform web
   ```

9. **Try it:** `docker compose up -d --build web`, then open `http://<host>:3500`, or `npx expo start` on a phone.
10. **Docs:** update the screens table in `docs/mobile.md` and `docs/project-status.md`.
