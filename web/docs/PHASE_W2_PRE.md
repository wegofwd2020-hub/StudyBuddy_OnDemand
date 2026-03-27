# Phase W2 — Student Portal: Core Learning Flow
## Pre-Implementation Document

Date: 2026-03-27
Status: Planning

---

## Scope

Build the authenticated student-facing portal. Students can log in, browse their
curriculum, read lessons (with audio), take quizzes, follow tutorials, run
experiments, view progress history, and see their stats and streak.

---

## Pages

| ID | Route | Description |
|---|---|---|
| S-01 | `/dashboard` | Streak counter, recent sessions, quick-resume card |
| S-02 | `/subjects` | Grade-filtered subject grid → unit list |
| S-03 | `/curriculum` | Visual unit grid with completion badges |
| S-04 | `/lesson/[unit_id]` | Lesson text + audio player (CDN pre-signed URL) |
| S-05 | `/quiz/[unit_id]` | Multiple-choice quiz, immediate feedback, score screen |
| S-06 | `/tutorial/[unit_id]` | Step-by-step tutorial renderer |
| S-07 | `/experiment/[unit_id]` | Lab guide: materials, steps, safety notes |
| S-08 | `/progress` | Session history timeline |
| S-09 | `/stats` | Accuracy trends, streak calendar, subject breakdown |
| S-14 | `/paywall` | Shown when backend returns HTTP 402 |

---

## New Files

```
web/
  app/(student)/
    layout.tsx                    ← Protected layout; redirect to /login if no session
    dashboard/page.tsx
    subjects/page.tsx
    curriculum/page.tsx
    lesson/[unit_id]/page.tsx
    quiz/[unit_id]/page.tsx
    tutorial/[unit_id]/page.tsx
    experiment/[unit_id]/page.tsx
    progress/page.tsx
    stats/page.tsx
    paywall/page.tsx

  components/
    layout/StudentNav.tsx          ← Sidebar nav (Dashboard, Subjects, Map, Progress, Stats)
    content/
      LessonRenderer.tsx           ← Renders lesson JSON (title, body sections, key_points)
      AudioPlayer.tsx              ← <audio> element with CDN URL; play/pause/progress bar
      QuizPlayer.tsx               ← Question-by-question state machine; score screen
      TutorialRenderer.tsx         ← Numbered step renderer
      ExperimentRenderer.tsx       ← Materials list + steps + safety callout
    feedback/
      FeedbackWidget.tsx           ← Thumbs up/down overlay; POST /feedback/submit
    student/
      StreakCard.tsx               ← Streak count + fire icon + calendar dots
      OfflineBanner.tsx            ← Detects navigator.onLine; shows warning banner
      StatCard.tsx                 ← Reusable KPI card for stats page

  lib/
    types/api.ts                   ← TypeScript interfaces for all backend responses
    api/
      curriculum.ts                ← getCurriculumTree()
      content.ts                   ← getLesson(), getQuiz(), getTutorial(), getExperiment(),
                                      getLessonAudioUrl()
      progress.ts                  ← startSession(), submitAnswer(), endSession(), getHistory()
      analytics.ts                 ← startLessonView(), endLessonView(), getStudentStats()
      feedback.ts                  ← submitFeedback()
    hooks/
      useCurriculumTree.ts
      useLesson.ts
      useQuiz.ts
      useProgress.ts
      useStats.ts
    providers/
      QueryProvider.tsx            ← TanStack Query client wrapper

  tests/unit/
    quiz-state.test.ts             ← Quiz state machine logic
    feedback.test.ts               ← Feedback widget submit behaviour
    offline-banner.test.tsx        ← navigator.onLine mock
```

---

## API Endpoints Used

| Endpoint | Used by |
|---|---|
| `GET /curriculum/tree` | S-02, S-03 |
| `GET /content/{unit_id}/lesson` | S-04 |
| `GET /content/{unit_id}/lesson/audio` | S-04 (returns pre-signed URL) |
| `GET /content/{unit_id}/quiz` | S-05 |
| `GET /content/{unit_id}/tutorial` | S-06 |
| `GET /content/{unit_id}/experiment` | S-07 |
| `POST /progress/session/start` | S-04, S-05 |
| `POST /progress/answer` | S-05 |
| `POST /progress/session/end` | S-05 |
| `GET /progress/history` | S-01, S-08 |
| `POST /analytics/lesson/start` | S-04 |
| `POST /analytics/lesson/end` | S-04 |
| `GET /analytics/student/stats` | S-09 |
| `POST /feedback/submit` | S-04, S-05, S-07 |

---

## Key Design Decisions

### 1. Server vs Client components
- **Server components**: layout auth guard, dashboard initial data, progress history
- **Client components**: quiz state machine, audio player, feedback widget, offline banner,
  stats charts (Recharts requires browser APIs)

### 2. Auth guard
The `(student)/layout.tsx` calls `auth0.getSession()` server-side. If no session,
it redirects to `/login`. The internal backend JWT is read from
`session.tokenSet.accessToken` (Auth0 access token) — in production, this is
exchanged for an internal backend JWT via `/auth/exchange` on first login and
stored in the session.

For Phase W2, the axios client reads `sb_token` from `localStorage`; the login
callback stores it there after exchange. This is sufficient for dev/staging testing.

### 3. Quiz state machine
Pure client-side state (no server round-trip between questions):
```
LOADING → ANSWERING → REVIEWING → (next question | SCORING)
```
`POST /progress/answer` is fire-and-forget (non-blocking) after each answer.
`POST /progress/session/end` is called once on the final question.

### 4. Paywall interception
The axios interceptor already handles `401`. Add a `402` interceptor that sets a
module-level flag and triggers a redirect to `/paywall`. Content pages check this
before rendering.

### 5. Audio player
Fetches CDN pre-signed URL from `GET /content/{unit_id}/lesson/audio`, then sets
the `<audio>` element `src` to that URL. The API server is never in the audio
data path (per CLAUDE.md rule #3).

### 6. Streak logic
Streak count is returned by `GET /analytics/student/stats`. No client-side
computation. The calendar heatmap on the stats page renders from
`session_dates` array in the stats response.

---

## Exit Criteria

- [ ] All 10 pages render without errors
- [ ] Protected routes redirect unauthenticated users to `/login`
- [ ] Full lesson → quiz → score flow works end-to-end against staging backend
- [ ] 402 response shows paywall page (not a blank error)
- [ ] Audio player requests CDN URL; does not proxy bytes through API
- [ ] Unit tests pass: quiz state machine, feedback widget, offline banner
- [ ] TypeScript type check: 0 errors
- [ ] Production build: 0 errors
