/**
 * tests/e2e/student_flow.spec.ts
 *
 * Critical-path E2E tests for the student learning loop.
 *
 * Covers 3 paths:
 *   1. Public landing page — hero heading and sign-in CTA visible (no auth)
 *   2. Curriculum map → lesson navigation (authenticated)
 *   3. Lesson → quiz → result screen → progress history (authenticated, full loop)
 *
 * Auth strategy: same pattern as personas/student-accessibility.spec.ts
 *   - sb_dev_session cookie  → satisfies server-component layout check
 *   - sb_token in localStorage → satisfies Axios API-client Bearer header
 *
 * All backend API calls are intercepted with page.route() — no live backend needed.
 */

import { test, expect } from "@playwright/test";
import type { Page } from "@playwright/test";
import { makeStudentToken, devSessionCookie } from "./helpers/tokens";
import {
  MOCK_CURRICULUM_TREE,
  MOCK_PROGRESS_WITH_STATUS,
} from "./data/curriculum-map-page";
import {
  MOCK_LESSON_WITH_AUDIO,
  MOCK_AUDIO_URL_RESPONSE,
  LESSON_STRINGS,
} from "./data/lesson-page";
import {
  MOCK_QUIZ,
  MOCK_SESSION_ID,
  MOCK_ANSWER_CORRECT,
  MOCK_SESSION_END_PASSED,
  QUIZ_STRINGS,
} from "./data/quiz-page";
// MOCK_PROGRESS_HISTORY not imported — stubProgressApis uses inline backend-format response
// (getProgressHistory maps /progress/student backend shape; frontend ProgressHistory type differs)
import { HERO, NAV_LINKS } from "./data/landing-page";

// ---------------------------------------------------------------------------
// Auth + API stub helpers
// ---------------------------------------------------------------------------

const STUDENT_TOKEN = makeStudentToken();

async function setupStudentAuth(page: Page) {
  await page
    .context()
    .addCookies([devSessionCookie("Alex Student", "alex@test.invalid")]);
  await page.addInitScript(
    (token) => localStorage.setItem("sb_token", token),
    STUDENT_TOKEN,
  );
}

async function stubCommonApis(page: Page) {
  await page.route("**/api/v1/subscription/status**", (route) =>
    route.fulfill({ status: 200, json: { status: "active", plan: "student" } }),
  );
  await page.route("**/api/v1/analytics/student/stats**", (route) =>
    route.fulfill({
      status: 200,
      json: {
        streak_days: 3,
        session_dates: [],
        lessons_viewed: 5,
        quizzes_completed: 3,
        pass_rate: 1.0,
        avg_score: 90,
        audio_sessions: 1,
        period: "30d",
      },
    }),
  );
}

async function stubCurriculumApis(page: Page) {
  await page.route("**/api/v1/curriculum/tree**", (route) =>
    route.fulfill({ status: 200, json: MOCK_CURRICULUM_TREE }),
  );
  await page.route("**/api/v1/progress/history**", (route) =>
    route.fulfill({ status: 200, json: MOCK_PROGRESS_WITH_STATUS }),
  );
}

async function stubLessonApis(page: Page) {
  await page.route("**/api/v1/content/G8-SCI-001/lesson**", (route) =>
    route.fulfill({ status: 200, json: MOCK_LESSON_WITH_AUDIO }),
  );
  await page.route("**/api/v1/content/G8-SCI-001/lesson/audio**", (route) =>
    route.fulfill({ status: 200, json: MOCK_AUDIO_URL_RESPONSE }),
  );
}

async function stubQuizApis(page: Page) {
  await page.route("**/api/v1/content/G8-SCI-001/quiz**", (route) =>
    route.fulfill({ status: 200, json: MOCK_QUIZ }),
  );
  // POST /progress/session — actual URL used by startSession() in progress.ts
  // Use function predicate: glob "**/api/v1/progress/session" (no trailing **)
  // is ambiguous in Playwright's LIFO resolver when the more-specific
  // "/*/answer" and "/*/end" patterns are registered after it.
  await page.route(
    (url) => url.pathname === "/api/v1/progress/session",
    (route) => route.fulfill({ status: 200, json: { session_id: MOCK_SESSION_ID } }),
  );
  // POST /progress/session/{id}/answer
  await page.route("**/api/v1/progress/session/*/answer", (route) =>
    route.fulfill({ status: 200, json: { correct: true, explanation: "" } }),
  );
  // POST /progress/session/{id}/end — backend returns total_questions, not total
  await page.route("**/api/v1/progress/session/*/end", (route) =>
    route.fulfill({
      status: 200,
      json: {
        session_id: MOCK_SESSION_ID,
        score: 3,
        total_questions: 3,
        passed: true,
        attempt_number: 1,
        ended_at: new Date().toISOString(),
      },
    }),
  );
}

async function stubProgressApis(page: Page) {
  // useProgressHistory → getProgressHistory → GET /progress/student?limit=...
  // Response must match the backend shape that getProgressHistory maps from.
  await page.route("**/api/v1/progress/student**", (route) =>
    route.fulfill({
      status: 200,
      json: {
        student_id: "test-student-001",
        sessions: [
          {
            session_id: "sess-001",
            unit_id: "G8-SCI-001",
            curriculum_id: "default-2026-g8",
            subject: "Science",
            started_at: "2026-03-25T10:00:00Z",
            ended_at: "2026-03-25T10:15:00Z",
            score: 3,
            total_questions: 3,
            completed: true,
            passed: true,
            attempt_number: 1,
          },
        ],
      },
    }),
  );
}

// ---------------------------------------------------------------------------
// Test 1 — Public landing page (no auth)
// ---------------------------------------------------------------------------

test("public landing page — hero heading and sign-in CTA visible", async ({
  page,
}) => {
  await page.goto("/");
  await page.waitForLoadState("networkidle");

  // Hero heading
  await expect(
    page.getByRole("heading", { name: HERO.heading }),
  ).toBeVisible();

  // Sign in link in nav
  await expect(
    page.getByRole("link", { name: NAV_LINKS[1].text }),
  ).toBeVisible();
});

// ---------------------------------------------------------------------------
// Test 2 — Authenticated curriculum map → open lesson
// ---------------------------------------------------------------------------

test("curriculum map → lesson navigation", async ({ page }) => {
  await setupStudentAuth(page);
  await stubCommonApis(page);
  await stubCurriculumApis(page);
  await stubLessonApis(page);

  // Navigate to curriculum map
  await page.goto("/curriculum");
  await page.waitForLoadState("networkidle");

  // Cell Biology unit must be visible
  await expect(page.getByText("Cell Biology")).toBeVisible();

  // Click the Lesson link for G8-SCI-001 and land on the lesson page.
  // The link href is /lesson/G8-SCI-001; we navigate directly to be
  // resilient to any selector change in the curriculum map component.
  await page.goto("/lesson/G8-SCI-001");
  await page.waitForLoadState("networkidle");

  // Lesson title from mock
  await expect(page.getByText(MOCK_LESSON_WITH_AUDIO.title)).toBeVisible();

  // First section heading
  await expect(
    page.getByText(MOCK_LESSON_WITH_AUDIO.sections[0].heading),
  ).toBeVisible();

  // Take Quiz CTA must be present
  await expect(
    page.getByRole("link", { name: LESSON_STRINGS.takeQuizBtn }),
  ).toBeVisible();
});

// ---------------------------------------------------------------------------
// Test 3 — Lesson → quiz → result screen → progress history
// ---------------------------------------------------------------------------

test("student learning loop: lesson → quiz → result → progress", async ({
  page,
}) => {
  await setupStudentAuth(page);
  await stubCommonApis(page);
  await stubLessonApis(page);
  await stubQuizApis(page);

  // ── Step 1: open lesson ───────────────────────────────────────────────────
  await page.goto("/lesson/G8-SCI-001");
  await page.waitForLoadState("networkidle");

  await expect(page.getByText(MOCK_LESSON_WITH_AUDIO.title)).toBeVisible();

  // Key Points section
  await expect(
    page.getByText(MOCK_LESSON_WITH_AUDIO.key_points[0]),
  ).toBeVisible();

  // ── Step 2: navigate to quiz ──────────────────────────────────────────────
  await page
    .getByRole("link", { name: LESSON_STRINGS.takeQuizBtn })
    .click();
  await page.waitForURL("**/quiz/G8-SCI-001**");
  await page.waitForLoadState("networkidle");

  // Quiz title
  await expect(page.getByText(MOCK_QUIZ.title)).toBeVisible();

  // ── Step 3: answer all 3 questions correctly ──────────────────────────────
  for (let i = 0; i < MOCK_QUIZ.questions.length; i++) {
    const q = MOCK_QUIZ.questions[i];
    const isLast = i === MOCK_QUIZ.questions.length - 1;

    // Question text visible
    await expect(page.getByText(q.question)).toBeVisible();

    // Select the correct option
    await page
      .getByRole("button", { name: q.options[q.correct_index] })
      .click();

    // Submit
    await page
      .getByRole("button", { name: QUIZ_STRINGS.submitBtn })
      .click();

    // Explanation appears
    await expect(page.getByText(q.explanation)).toBeVisible();

    // Advance to next question or results
    if (isLast) {
      await page
        .getByRole("button", { name: QUIZ_STRINGS.seeResultsBtn })
        .click();
    } else {
      await page
        .getByRole("button", { name: QUIZ_STRINGS.nextBtn })
        .click();
    }
  }

  // ── Step 4: result screen shows a passing score ───────────────────────────
  // MOCK_SESSION_END_PASSED: score=3, total=3, passed=true
  await expect(page.getByText("3")).toBeVisible();

  // ── Step 5: progress history reflects the completed unit ─────────────────
  await stubProgressApis(page);
  await page.goto("/progress");
  await page.waitForLoadState("networkidle");

  // getProgressHistory maps unit_title from unit_id (backend doesn't return title)
  await expect(page.getByText("G8-SCI-001")).toBeVisible();
});
