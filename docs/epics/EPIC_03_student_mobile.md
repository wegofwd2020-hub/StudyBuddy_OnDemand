# Epic 3 — Student Mobile App

**Status:** 💭 Your call

---

## What it is

Improve the student-facing mobile experience: the current Kivy app is a thin
client built for offline-first study. This epic covers either hardening the
existing Kivy app for a real release, or replacing it with a React Native / Expo
app that shares components with the existing Next.js web frontend.

---

## Current state

A Kivy (Python) mobile app exists at `mobile/`. It is a thin client:

- Reads curriculum metadata from `data/*.json` (grade-level JSON files)
- Fetches lesson/quiz content from the backend API
- Caches content in SQLite for offline access
- Queues progress + analytics events in SQLite `event_queue`, synced on foreground
- Has a `SyncManager`, `LocalCache`, `ProgressQueue`, and `CurriculumResolver`
- i18n for EN/FR/ES UI strings
- No production build pipeline exists (no APK, no app store listing)

**Key gap:** The Kivy app was built as a proof-of-concept. It has no tests for UI
screens, no accessibility support verified, no production signing/build pipeline,
and no feature parity with the web portal's school features (classrooms, reports).

The `mobile/ARCHITECTURE.md` file exists (recently added) but content unknown.

---

## Why it matters

Students are the end users. Most K-12 students study on a phone. A polished,
offline-capable mobile experience is the product's core value proposition for
students in low-bandwidth environments.

---

## Two paths

### Path A — Harden the Kivy app
Continue with Python/Kivy. Better for teams with Python skills and no
React Native experience. Lower rewrite risk but Kivy has limited community
support, poor accessibility tooling, and no component sharing with the web frontend.

### Path B — React Native / Expo rewrite
Rewrite the student app in React Native (Expo). Shares TypeScript types, API
client code, and some UI logic with the Next.js web frontend. Better long-term
maintainability, stronger accessibility (React Native Accessibility API), and
a proper app store build pipeline via EAS Build.

---

## Rough scope (Path B — React Native)

| Phase | What gets built |
|---|---|
| H-1 | Expo project setup, shared `lib/api/` types from web, Auth0 login flow |
| H-2 | Student home screen: subject cards, unit list, lesson viewer |
| H-3 | Quiz flow: question display, answer selection, results screen |
| H-4 | Offline sync: SQLite cache, event queue, SyncManager (port from Kivy) |
| H-5 | Audio player, progress screen, streak display |
| H-6 | EAS Build pipeline: staging APK + iOS TestFlight |

---

## Open questions

1. **Kivy or React Native?** This is the biggest decision. What's the team's React Native experience?
2. **Target platform:** Android only, iOS only, or both from day one?
3. **Offline depth:** Full offline (download entire curriculum) or lightweight offline (cache last-viewed lessons only)?
4. **Student auth:** Students currently use Auth0 or local auth (school-provisioned). Should mobile support both auth tracks from launch?
5. **Feature scope at v1:** Lessons + quizzes only, or also tutorials and experiments?
6. **App store:** Private TestFlight/internal track first, or public release from day one?

---

## Your decisions / notes

> Add your thoughts here. Even rough bullet points are enough to start.

-
-
-
