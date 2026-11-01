---
name: release-mobile
description: Build and ship the ChitBook Expo app - Android APK/AAB, iOS build, store submission, or an over-the-air (EAS Update) JS fix. Use when asked to build, release, or publish the phone app.
---

# Release the mobile app

Before you start:
- From `apps/mobile`: `npm test && npm run typecheck && npm run lint && npx expo-doctor` all pass.
- `EXPO_PUBLIC_API_BASE_URL` points at the **public HTTPS** API. It's baked in at build time.
- The user has an Expo account (`npx eas-cli@latest login`). iOS also needs an Apple Developer account.

| Goal | Command (from `apps/mobile`) |
|---|---|
| Installable Android APK to share | `npx eas-cli@latest build -p android --profile preview` |
| Play Store build | `npx eas-cli@latest build -p android --profile production` |
| App Store build | `npx eas-cli@latest build -p ios --profile production` |
| Submit to stores | `npx eas-cli@latest submit -p android` / `-p ios` |
| JS-only fix, no store review | `npx eas-cli@latest update --branch production -m "fix: ..."` |

Steps:

1. Bump `version` in `app.json` for store releases. Build numbers auto-increment (`eas.json`).
2. Run the build command and share the build URL / QR code that EAS prints.
3. OTA updates only work for JS/asset changes. Native changes (new native package, `app.json` plugins) need a new build.
4. Note the release in `docs/project-status.md`.

These are outward-facing actions: confirm with the user before `submit` or a production `update`.
