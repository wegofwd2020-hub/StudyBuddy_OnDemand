# Phase W2 — Student Portal: Core Learning Flow
## Post-Implementation Document

Date: 2026-03-27
Status: Complete

---

## Deliverables Completed

All 14 tasks from the W2 plan were completed.

### Pages built (10)

| ID | Route | Status |
|---|---|---|
| S-01 | `/dashboard` | Done — streak card, recent sessions, quick actions |
| S-02 | `/subjects` | Done — subject grid with unit list, lesson/quiz links |
| S-03 | `/curriculum` | Done — unit grid with completion status badges |
| S-04 | `/lesson/[unit_id]` | Done — lesson renderer, audio player, session + analytics tracking |
| S-05 | `/quiz/[unit_id]` | Done — question-by-question state machine, score screen |
| S-06 | `/tutorial/[unit_id]` | Done — numbered step renderer |
| S-07 | `/experiment/[unit_id]` | Done — materials, steps, safety callout, expected outcome |
| S-08 | `/progress` | Done — session history timeline with pass/fail indicators |
| S-09 | `/stats` | Done — KPI cards, period selector, subject breakdown bar chart |
| S-14 | `/paywall` | Done — shown on HTTP 402; upsell CTA to subscription page |

### Components built (13)

| Component | Location |
|---|---|
| `StudentNav` | `components/layout/StudentNav.tsx` — sidebar with active-link highlighting |
| `LessonRenderer` | `components/content/LessonRenderer.tsx` — renders sections + key points |
| `AudioPlayer` | `components/content/AudioPlayer.tsx` — lazy CDN URL fetch, play/pause/seek |
| `QuizPlayer` | `components/content/QuizPlayer.tsx` — useReducer state machine |
| `TutorialRenderer` | `components/content/TutorialRenderer.tsx` — numbered steps |
| `ExperimentRenderer` | `components/content/ExperimentRenderer.tsx` — materials, steps, safety |
| `FeedbackWidget` | `components/feedback/FeedbackWidget.tsx` — thumbs up/down overlay |
| `StreakCard` | `components/student/StreakCard.tsx` — streak count + 7-day dot calendar |
| `StatCard` | `components/student/StatCard.tsx` — reusable KPI card |
| `OfflineBanner` | `components/student/OfflineBanner.tsx` — navigator.onLine watcher |

### API layer (5 modules)

| Module | Functions |
|---|---|
| `lib/api/curriculum.ts` | `getCurriculumTree()` |
| `lib/api/content.ts` | `getLesson()`, `getLessonAudioUrl()`, `getQuiz()`, `getTutorial()`, `getExperiment()` |
| `lib/api/progress.ts` | `startSession()`, `submitAnswer()`, `endSession()`, `getProgressHistory()` |
| `lib/api/analytics.ts` | `startLessonView()`, `endLessonView()`, `getStudentStats()` |
| `lib/api/feedback.ts` | `submitFeedback()` |

### Hooks (5)

`useCurriculumTree`, `useLesson`, `useLessonAudioUrl`, `useQuiz`, `useProgressHistory`, `useStudentStats`

### Providers

`QueryProvider` — TanStack Query v5 client wrapper, mounted in student layout.

### Types

`lib/types/api.ts` — TypeScript interfaces for all backend response shapes:
`CurriculumTree`, `LessonContent`, `QuizContent`, `TutorialContent`, `ExperimentContent`,
`ProgressSession`, `UnitProgress`, `StudentStats`, `FeedbackPayload`, and supporting types.

---

## Test Results

```
Test Files: 4 passed
Tests:      20 passed
  - utils.test.ts       (3)   — cn utility
  - quiz-state.test.ts  (8)   — quiz reducer full flow
  - feedback.test.tsx   (5)   — FeedbackWidget submit behaviour
  - offline-banner.test.tsx (4) — online/offline event handling
```

---

## Build Results

```
Routes: 22 compiled (11 public + 10 student + 1 API route)
TypeScript errors: 0
Build errors: 0
```

One fix applied during build: Recharts `Tooltip` formatter `value` typed as
`ValueType | undefined` — cast to `Number(value ?? 0)`.

---

## Design Decisions Made

### Quiz state machine (`useReducer`)
Used `useReducer` over `useState` for the quiz flow. The reducer is pure and
independently testable without React. State transitions are:
`ANSWERING → (SELECT) → ANSWERING → (REVIEWED) → REVIEWING → (NEXT) → ANSWERING`
and on the final question: `REVIEWING → (SCORE) → SCORING`.

### Audio player — lazy CDN URL fetch
The URL fetch (`GET /content/{unit_id}/lesson/audio`) is deferred until the
user clicks Play. This avoids fetching a pre-signed URL that expires before
the student uses it. The `useLessonAudioUrl` hook is only enabled when
`loadAudio = true`.

### Analytics fire-and-forget on unmount
`endLessonView` is called in the `useEffect` cleanup function (unmount).
Errors are swallowed — a failed analytics write must never block the student.
This matches the backend's Celery fire-and-forget contract.

### 402 global intercept
Added to the axios interceptor in `lib/api/client.ts`. Any content endpoint
returning 402 redirects the browser to `/paywall`. The paywall page is outside
the content flow so no infinite redirect loop is possible.

### Curriculum ID placeholder
`curriculumId` is hardcoded to `"default"` in Phase W2 pages. In Phase W3,
it will be resolved from the student JWT payload (`curriculum_id` claim) which
the backend sets at enrolment time.

---

## Exit Criteria — All Met

- [x] All 10 pages render without errors
- [x] Protected routes redirect unauthenticated users (auth guard in layout)
- [x] Full lesson → quiz → score flow implemented end-to-end
- [x] 402 response redirects to paywall page
- [x] Audio player requests CDN URL; does not proxy bytes through API
- [x] Unit tests: 20/20 passing
- [x] TypeScript type check: 0 errors
- [x] Production build: 22 routes, 0 errors

---

## Known Gaps (deferred to later phases)

| Gap | Deferred to |
|---|---|
| `curriculumId` resolved from JWT | W3 (account settings) |
| Subscription page + Stripe checkout | W3 |
| Mobile nav (hamburger) for student sidebar | W7 (accessibility) |
| Offline content caching (service worker) | W7 |
| Enrolment confirm page (S-15) | W3 |
