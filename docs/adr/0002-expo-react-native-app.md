# ADR 0002: React Native + Expo for Android, iOS and web

- **Status:** accepted · 2026-11-01

## Context

- We need one codebase for Android and iOS, and ideally web too, maintained long-term.

## Options

| Option | For | Against |
|---|---|---|
| **React Native + Expo** | TypeScript (largest ecosystem); cloud builds without a Mac (EAS); over-the-air JS updates; web from the same code | native UI differences need care |
| Flutter | consistent rendering; good performance | Dart (smaller ecosystem); no code reuse with web tooling |

## Decision

- React Native with **Expo** (managed workflow, Continuous Native Generation).
- **expo-router** for navigation and **TanStack Query** for server state.
- **expo-secure-store** for the refresh token.

## Consequences

- `ios/` and `android/` folders are generated, never edited. Native config lives in `app.json`.
- Store builds and updates run through EAS. An iOS release needs an Apple Developer account.
