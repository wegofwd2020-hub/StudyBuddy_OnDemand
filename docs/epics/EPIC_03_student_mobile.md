# Epic 3 — Student Mobile App (Expo / React Native)

**Status:** ✅ Path B chosen (2026-04-14) — not yet started; parked behind testing phase and hosting decision.

---

## What it is

Rewrite the student-facing mobile app in Expo / React Native, sharing TypeScript
types, API clients, Zod schemas, and UI logic with the existing Next.js web
frontend. The existing Kivy app at `mobile/` is retained as a working reference
during the rewrite and deleted after feature parity.

---

## Decision record — Path B chosen (2026-04-14)

Path A (harden Kivy) was considered and rejected. Reasons:

| Factor | Why Path B wins |
|---|---|
| Accessibility (Epic 9 + WCAG 2.1 AA) | RN Accessibility API is first-class; Kivy has no mature a11y tooling |
| Code sharing with Next.js web | TypeScript types, API clients, `next-intl` JSON, Zod schemas, hooks all reuse |
| Team fit | Team already ships React + TS + Tailwind on the web — Expo is the same stack |
| Android build pipeline | EAS Build is standard; `buildozer` / python-for-android produces large slow APKs |
| iOS story | Expo supports iOS in the same codebase; Kivy on iOS is impractical |
| App store submission | Expo EAS Submit is mature; Kivy path is bespoke |
| Offline-first | `expo-sqlite` + `expo-file-system` + `@react-native-community/netinfo` cover every current Kivy capability |
| Architecture reusability | `mobile/ARCHITECTURE.md` (committed 2026-04-14) is substrate-agnostic — personas, offline sync, auth flow, API contract all transfer |

Path A remained viable only under a narrow scenario (single-partner Android-only
pilot, no accessibility target) which does not match this product's positioning.

---

## Current state — what exists to port from

| Area | Kivy reference | Port strategy |
|---|---|---|
| Screens | 12 Kivy screens: Login, Tutorial, Quiz, Dashboard, Subject, Progress, Stats, Experiment, Result, Subscription, Settings, CurriculumMap | Redesign per Rule #18 typography; rebuild as RN components |
| API clients | `mobile/src/api/` — auth, content, progress, subscription, analytics | Extract to shared `packages/api-client` consumed by both `web/` and `mobile-rn/` |
| Offline sync | `SyncManager`, `LocalCache`, `EventQueue` in `mobile/src/logic/` | Port logic, swap Kivy/Python SQLite for `expo-sqlite` |
| i18n | `mobile/i18n/{en,fr,es}.json` | Extract to shared `packages/i18n`; reuse in web + mobile-rn |
| Architecture | `mobile/ARCHITECTURE.md` — 14 sections, 1135 lines | Treat as the spec; substrate-agnostic content maps directly to RN |
| Known gaps (from ARCHITECTURE.md) | ProgressQueue, CurriculumResolver, network listener, centralised error types | Build correctly the first time in RN rather than backporting to Kivy |

---

## Why it matters

Students are the end users. Most K-12 students study on a phone. An accessible,
offline-capable mobile experience is the product's core value proposition for
students in low-bandwidth environments. The Next.js web portal is the teacher /
school-admin surface; the mobile app is where students actually live.

---

## Phased scope

### Wave 1 — Monorepo foundation

| Phase | What gets built | Size |
|---|---|---|
| M-1 | Convert root to pnpm workspace (or Turborepo). Extract `packages/api-client`, `packages/schemas` (Zod), `packages/i18n`. Make `web/` consume them. No behaviour change. | M |
| M-2 | Scaffold `mobile-rn/` — Expo SDK 51+, Expo Router, TypeScript strict, EAS project. Consumes the shared packages from M-1. | S |
| M-3 | CI: lint + type-check + unit tests for `mobile-rn/` in GitHub Actions. Add `mobile-rn/` to existing `test.yml` workflow. | S |

### Wave 2 — Auth + shell

| Phase | What gets built | Size |
|---|---|---|
| M-4 | Auth0 PKCE flow via `expo-auth-session`; secure token storage via `expo-secure-store`; token refresh interceptor in shared `api-client`. | M |
| M-5 | Local auth (school-provisioned, email+password) — supports the third auth track shipped in Phase A. Respects `first_login=true` → forced reset screen. | S |
| M-6 | App shell: Expo Router tabs (Home / Progress / Settings), theme tokens from web (OKLch CSS-variables → RN equivalent via `useColorScheme` + theme context), Rule #18 font stack via `expo-font`. | M |

### Wave 3 — Learning core (standard student persona)

| Phase | What gets built | Size |
|---|---|---|
| M-7 | Subject cards + unit list (home screen). Consumes existing `/api/v1/content/*` endpoints. | S |
| M-8 | Lesson viewer: Markdown via `react-native-markdown-display`; Mermaid diagrams (via `react-native-svg` stub or WebView); JetBrains Mono for equations. | M |
| M-9 | Audio player: pre-signed CDN URL → `expo-av`; transcript toggle (wires up Epic 9 I-12). | S |
| M-10 | Quiz flow: MCQ UI, answer selection, results screen, fire-and-forget `POST /progress/answer`. | M |
| M-11 | Experiment viewer: ports ExperimentScreen behaviour from Kivy; renders canonical-unit measurements via `<Measurement>` component (Epic 8 H-5). | M |

### Wave 4 — Offline-first

| Phase | What gets built | Size |
|---|---|---|
| M-12 | `LocalCache` on `expo-sqlite`: content JSON keyed by `unit_id + curriculum_id + content_version + lang`; LRU eviction under `MAX_CACHE_MB`. | M |
| M-13 | `EventQueue` on `expo-sqlite`: progress + analytics events with UUID `event_id`; backend deduplicates via `ON CONFLICT DO NOTHING`. | S |
| M-14 | `SyncManager`: foreground-resume flush **plus** `@react-native-community/netinfo` network-state listener (closes a Known Gap from ARCHITECTURE.md). | M |
| M-15 | Audio cache on `expo-file-system`: MP3 files keyed by CloudFront URL hash; size budget separate from content cache. | S |
| M-16 | Centralised error types + exponential backoff (closes another Known Gap). | S |

### Wave 5 — School-enrolled student features

| Phase | What gets built | Size |
|---|---|---|
| M-17 | Curriculum resolver on device: restrict-access filter, classroom assignment awareness (closes Known Gap). | M |
| M-18 | Subscription paywall intercept: 402 from backend → Stripe Checkout in system browser via `expo-web-browser`; deep-link back to app. | S |
| M-19 | Progress dashboard, streak counter, history screen (port from Kivy). | M |

### Wave 6 — Release readiness

| Phase | What gets built | Size |
|---|---|---|
| M-20 | Accessibility pass: RN Accessibility API coverage, VoiceOver + TalkBack testing, focus order, contrast audit. | M |
| M-21 | Crash reporting + structured logging (Sentry or equivalent); offline-safe log buffer. | S |
| M-22 | EAS Build: staging Android (APK internal track) + iOS (TestFlight). | M |
| M-23 | Play Store + App Store submission: privacy manifests (COPPA data-safety form, FERPA disclosures), icons, screenshots, store copy. | M |
| M-24 | Delete `mobile/` Kivy tree after production release sign-off. | S |

---

## Decisions locked (2026-04-14)

| # | Question | Decision | Rationale |
|---|---|---|---|
| Q1 | Monorepo tool | **pnpm workspaces** | Lightest option; no Turborepo/Nx overhead for a 2-app repo. Remote build caching can be added later if CI time becomes an issue. |
| Q2 | RN New Architecture (Fabric / TurboModules) | **Opt in from day one** | Expo SDK 51+ makes it a toggle. Starting on the new arch avoids a painful migration later; Expo 52 makes it default anyway. |
| Q3 | Offline depth | **Cache-on-tap** | Matches current Kivy behaviour, ships faster, lets device storage decisions stay in the user's control. Full-curriculum prefetch can be added later as a per-school opt-in. |
| Q4 | Single codebase vs two | **Single Expo codebase** | Divergences (status bar, back button, notification prompts, store manifests) are small and handled via `Platform.OS` or `.ios.tsx`/`.android.tsx` overrides. Two projects would duplicate every screen for no payoff. |
| Q5 | Deep-linking scheme | **`studybuddy://` for dev and early testing; universal links (`https://…`) added alongside at M-22** | Custom scheme ships today, no infra needed, good enough for internal TestFlight / Play internal track. Apple and Google store review will **reject** a production app that uses a custom scheme for OAuth callbacks — so M-22 (EAS Build for stores) must add universal links. Custom scheme retained as a fallback for debug tooling. Gated on hosting (domain + `.well-known` files). |
| Q6 | Kivy app transition | **Hard cutover at M-24** | Kivy tree deleted from repo once the Expo app passes store review and is live in production. No dual-running, no "migrate to the new app" prompt inside the Kivy version. Simpler to operate; avoids carrying two codepaths through support incidents. **Pre-M-24 check:** confirm no users are still on the Kivy app by checking `/admin/analytics` for recent sessions from the Kivy `X-App-Version` header. |
| Q7 | Release cadence | **Expo Updates (OTA) for JS-only changes; store releases for native / manifest changes** | JS-only patches (bug fixes, copy changes, small feature toggles) push instantly via Expo Updates — no store review. Native-module upgrades, permission additions, SDK bumps, and `app.json` changes require a full store build. **Channel strategy:** `staging` branch auto-deploys OTA to TestFlight + Play internal track; `production` branch requires a manual promote. Monitor for school IT policies that block OTA (rare but possible); if encountered, fall back to pinned store builds for that tenant. |

## Open questions

_All closed on 2026-04-14. Epic is ready to schedule once testing phase wraps and Epic 2 hosting is settled._

---

## Dependencies

- **Epic 2 (Hosting)** — deep-link domain (Q5) and production Auth0 tenant gate M-4 and M-22.
- **Epic 8 (Onboarding Completeness)** — `<Measurement>` component (H-5) is reused by M-11 experiments.
- **Epic 9 (Accessibility & Personalization)** — shared theme tokens (I-9) reused by M-6; transcript toggle (I-12) reused by M-9; `packages/i18n` landed here but extracted in Epic 9 Wave 1.

Epic 3 can start as soon as Epic 2 hosting is settled. Monorepo extraction (Wave
1) has no external blockers and could begin at any time.

---

## Your decisions / notes

> Add your thoughts here. Even rough bullet points are enough to start.

- Path B chosen on 2026-04-14. Kivy app stays as reference; delete at M-24.
- 7 technical decisions locked on 2026-04-14 (pnpm, RN new arch, cache-on-tap, single codebase, `studybuddy://` + universal links at M-22, hard cutover at M-24, Expo Updates OTA).
- **M-22 must add `.well-known/apple-app-site-association` + `.well-known/assetlinks.json` to whatever production host Epic 2 picks.** Flagging here so it isn't forgotten when hosting lands.
- **Pre-M-24 gate:** check `/admin/analytics` `X-App-Version` distribution to confirm no active Kivy sessions before deleting the Kivy tree.
- **EAS Update channels:** wire `staging` and `production` channels in `eas.json` at M-22; staging auto-pushes on merge to main, production requires manual promote.
