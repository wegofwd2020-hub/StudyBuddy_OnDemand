/**
 * The reported symptom of #524, re-cast for the #532 defer-results flow and
 * asserted in a real browser: picking an option records the answer and Next
 * advances — navigation is never a dead end.
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
 *   - answers submit on pick (no per-question Submit button); "Next"/"Back"
 *     navigate and "Finish quiz" ends the session — the verdict is withheld
 *     until the end-of-quiz summary ("Your answers")
 *   - the summary renders "Score: {score}/{total} ({pct}%)"
 *     (web/i18n/en.json → result_screen.score_label) and
 *     "Attempt #{attempt}" (attempt_label)
 */
import { test, expect } from "@playwright/test";
import { loadFixture, loginAsStudentA } from "./fixture";

test.describe("quiz journey (live stack)", () => {
  test("picking an option records it and Next advances to the following question", async ({
    page,
  }) => {
    const fixture = loadFixture();
    await loginAsStudentA(page);
    await page.goto(`/quiz/${fixture.unit_quiz}`);

    await expect(page.getByText(/question 1 of/i)).toBeVisible({ timeout: 15000 });

    // Pick any option — it submits in the background; no verdict is shown.
    await page
      .getByRole("button", { name: /^Option /i })
      .first()
      .click();

    // No mid-quiz reveal: the summary heading must not be present yet.
    await expect(page.getByRole("heading", { name: /your answers/i })).toHaveCount(0);

    // Navigation advances. Before #524's fix the equivalent action was a dead button.
    await page.getByRole("button", { name: /^next$/i }).click();
    await expect(page.getByText(/question 2 of/i)).toBeVisible();
  });

  test("completing the quiz reaches a summary with a real score", async ({ page }) => {
    const fixture = loadFixture();
    await loginAsStudentA(page);
    await page.goto(`/quiz/${fixture.unit_quiz}`);
    await expect(page.getByText(/question 1 of/i)).toBeVisible({ timeout: 15000 });

    // Answer all three questions, moving with Next.
    for (let i = 0; i < 3; i++) {
      await page
        .getByRole("button", { name: /^Option /i })
        .first()
        .click();
      if (i < 2) {
        await page.getByRole("button", { name: /^next$/i }).click();
        await expect(
          page.getByText(new RegExp(`question ${i + 2} of`, "i")),
        ).toBeVisible();
      }
    }

    // Every question answered, so Finish goes straight to the summary.
    await page.getByRole("button", { name: /finish quiz/i }).click();
    await expect(page.getByRole("heading", { name: /your answers/i })).toBeVisible({
      timeout: 15000,
    });

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
