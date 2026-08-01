/**
 * The reported symptom of #524, asserted in a real browser:
 * "In Quiz - Submit is not taking me to the next question."
 *
 * No route mocks: this drives the real /signin form, the real
 * /quiz/{unit_id} page, and the real backend (POST /progress/answer,
 * POST /progress/{session_id}/end) via the `web` + `api` containers.
 *
 * Selectors were verified against the actual component
 * (web/components/content/QuizPlayer.tsx), not guessed:
 *   - "Question {n} of {total}" progress text
 *   - option buttons render as `Option {option_id}` (from the fixture's
 *     quiz content in backend/quiz_suite/seed.py), no other accessible
 *     name prefix
 *   - the action button reads "Submit answer" while answering, then
 *     "Next question" (or "See results" on the last question) once the
 *     server has graded the answer
 *   - the score screen renders "Score: {score}/{total} ({pct}%)"
 *     (web/i18n/en.json → result_screen.score_label) and
 *     "Attempt #{attempt}" (attempt_label)
 */
import { test, expect } from "@playwright/test";
import { loadFixture, loginAsStudentA } from "./fixture";

test.describe("quiz journey (live stack)", () => {
  test("submit reveals the verdict and advances to the next question", async ({
    page,
  }) => {
    const fixture = loadFixture();
    await loginAsStudentA(page);
    await page.goto(`/quiz/${fixture.unit_quiz}`);

    await expect(page.getByText(/question 1 of/i)).toBeVisible({ timeout: 15000 });

    // Pick any option and submit.
    await page
      .getByRole("button", { name: /^Option /i })
      .first()
      .click();
    await page.getByRole("button", { name: /submit answer/i }).click();

    // The verdict comes back from the real server, so the action button must
    // become "Next question". Before the fix this stayed on "Submit answer".
    await expect(page.getByRole("button", { name: /next question/i })).toBeVisible({
      timeout: 15000,
    });

    await page.getByRole("button", { name: /next question/i }).click();
    await expect(page.getByText(/question 2 of/i)).toBeVisible();
  });

  test("completing the quiz reaches a result screen with a real score", async ({
    page,
  }) => {
    const fixture = loadFixture();
    await loginAsStudentA(page);
    await page.goto(`/quiz/${fixture.unit_quiz}`);
    await expect(page.getByText(/question 1 of/i)).toBeVisible({ timeout: 15000 });

    // Walk all three questions.
    for (let i = 0; i < 3; i++) {
      await page
        .getByRole("button", { name: /^Option /i })
        .first()
        .click();
      await page.getByRole("button", { name: /submit answer/i }).click();
      const next = page.getByRole("button", { name: /next question|see results/i });
      await expect(next).toBeVisible({ timeout: 15000 });
      await next.click();
    }

    // The brief's original assertion here was `getByText(/\d+\s*\/\s*3|attempt/i)`,
    // matched against a single locator. Playwright's getByText runs in strict
    // mode: because the score screen always renders BOTH "Score: {n}/3 (...)"
    // and "Attempt #{n}" (web/i18n/en.json → result_screen.score_label /
    // .attempt_label), that alternation matches two elements at once and the
    // locator throws "strict mode violation" rather than ever resolving true
    // or false. Splitting into two precise, non-overlapping assertions checks
    // the same real-score requirement without the ambiguous match — this is a
    // locator-specificity fix, not a weakened assertion: both facts (a real
    // x/3 score and a real attempt number) are still required to pass.
    await expect(page.getByText(/score:\s*\d+\s*\/\s*3/i)).toBeVisible({
      timeout: 15000,
    });
    await expect(page.getByText(/attempt\s*#\d+/i)).toBeVisible();
  });
});
