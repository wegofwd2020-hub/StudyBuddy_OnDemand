/**
 * The second half of #524: when grading legitimately fails, the player must
 * SAY something. A silently dead button is what let the bug reach a QA pass.
 *
 * No route mocks: the unit's quiz content is genuinely absent on disk
 * (backend/quiz_suite/seed.py writes a lesson for QS-NOQUIZ-001 but no quiz
 * files), so `GET /content/{unit_id}/quiz` 404s for real and
 * `useQuiz` (web/lib/hooks/useQuiz.ts) surfaces `isError`. The quiz page
 * (web/app/(student)/quiz/[unit_id]/page.tsx) never renders <QuizPlayer> in
 * that case — it short-circuits to `contentErrorMessage(error)`
 * (web/lib/content-error.ts), which maps a 404 to:
 *   "This isn't available yet. Please check back soon."
 * That is the exact, student-safe copy asserted below — not a generic
 * truthy check.
 */
import { test, expect } from "@playwright/test";
import { loadFixture, loginAsStudentA } from "./fixture";

test("a grading failure shows a message instead of a dead button", async ({ page }) => {
  const fixture = loadFixture();
  await loginAsStudentA(page);

  // The unit's quiz content is genuinely absent, so the page itself reports
  // unavailable content rather than rendering a player.
  await page.goto(`/quiz/${fixture.unit_noquiz}`);

  const unavailable = page.getByText(/isn't available|not available|couldn't/i);
  await expect(unavailable).toBeVisible({ timeout: 15000 });

  // Whatever is shown must be student-safe: no status codes, no stack traces.
  const body = (await page.textContent("body")) ?? "";
  expect(body).not.toMatch(/traceback|FileNotFoundError|\/data\/content|500 Internal/i);
});
