/**
 * The second half of #524: when grading legitimately fails, the player must
 * SAY something. A silently dead button is what let the bug reach a QA pass.
 *
 * Two distinct failure surfaces are covered here, deliberately kept as two
 * separate tests because they hit different code paths:
 *
 *  1. "shows a message instead of a dead button" — the unit's quiz content is
 *     missing BEFORE the player ever mounts. The PAGE
 *     (web/app/(student)/quiz/[unit_id]/page.tsx) short-circuits on
 *     `useQuiz`'s `isError` to `contentErrorMessage(error)`
 *     (web/lib/content-error.ts) and never renders <QuizPlayer> at all.
 *
 *  2. "mid-quiz" — the quiz loads fine and <QuizPlayer> IS mounted and
 *     answering, but the grading call (POST /progress/session/{id}/answer)
 *     fails while the student is mid-quiz. This is the LITERAL #524 symptom
 *     ("Submit is not taking me to the next question"): before PR #528,
 *     `handleSubmit`'s rejection was swallowed and the button just sat there.
 *     #528 added QuizPlayer's `failed` state — the message "We couldn't save
 *     that answer. Check your connection and try again." and the action
 *     button relabeling from "Submit answer" to "Try again"
 *     (web/components/content/QuizPlayer.tsx). Nothing under web/tests
 *     exercised this path before this spec.
 *
 * No route mocks in either test: failures are induced by mutating the real
 * content store / cache so the real backend call really fails.
 */
import { execFileSync } from "node:child_process";
import path from "node:path";
import { test, expect } from "@playwright/test";
import { loadFixture, loginAsStudentA } from "./fixture";

// web/tests/e2e/quiz-suite -> repo root is four levels up.
const REPO_ROOT = path.resolve(__dirname, "..", "..", "..", "..");

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

test("a grading failure mid-quiz shows the failure message and 'Try again', not a dead button", async ({
  page,
}) => {
  const fixture = loadFixture();

  // Belt-and-braces guard on top of the ABSOLUTE CONSTRAINT (only ever touch
  // the quiz-suite fixture's own content-store directory): refuse outright if
  // the loaded fixture doesn't look like the quiz-suite fixture. The other 81
  // curricula / 1112 quiz files in the content store are real, cost real
  // money, and have no backup.
  if (
    !fixture.curriculum_id.startsWith("quizsuite-") ||
    !fixture.unit_quiz.startsWith("QS-")
  ) {
    throw new Error(
      `Refusing to mutate content store: unexpected fixture ids ` +
        `(curriculum_id=${fixture.curriculum_id}, unit_quiz=${fixture.unit_quiz})`,
    );
  }

  await loginAsStudentA(page);
  await page.goto(`/quiz/${fixture.unit_quiz}`);

  // The player mounted and is answering — this is the #524 reported path,
  // not the page-level "unavailable" short-circuit covered by the spec above.
  await expect(page.getByText(/question 1 of/i)).toBeVisible({ timeout: 15000 });

  // Make the NEXT grading call fail for real:
  //  (a) delete this fixture unit's own quiz-set files from the content
  //      store (scoped to fixture.curriculum_id/fixture.unit_quiz only —
  //      verified directly against the API before wiring into this spec:
  //      see task-8-report.md), and
  //  (b) evict the matching Redis content-cache keys. The GET /quiz call that
  //      rendered "Question 1 of ..." above already warmed
  //      content:{curriculum_id}:{unit_id}:quiz_set_{n}_en.json
  //      (backend/src/content/service.py::get_content_file, TTL 3600s), so a
  //      cached copy would otherwise paper over the on-disk deletion for the
  //      answer-grading lookup too (get_quiz_answer_key calls the same
  //      get_content_file).
  const contentDir = `/data/content/curricula/${fixture.curriculum_id}/${fixture.unit_quiz}`;
  execFileSync(
    "docker",
    [
      "compose",
      "exec",
      "-T",
      "api",
      "sh",
      "-c",
      `rm -f ${contentDir}/quiz_set_*_en.json`,
    ],
    { cwd: REPO_ROOT },
  );

  const redisPassword = execFileSync(
    "docker",
    ["compose", "exec", "-T", "api", "sh", "-c", "echo $REDIS_PASSWORD"],
    { cwd: REPO_ROOT },
  )
    .toString()
    .trim();
  const cacheKeys = [1, 2, 3].map(
    (n) => `content:${fixture.curriculum_id}:${fixture.unit_quiz}:quiz_set_${n}_en.json`,
  );
  execFileSync(
    "docker",
    [
      "compose",
      "exec",
      "-T",
      "redis",
      "redis-cli",
      "-a",
      redisPassword,
      "DEL",
      ...cacheKeys,
    ],
    { cwd: REPO_ROOT },
  );

  // Answer the now-ungraded question. The real POST 404s ("quiz_not_found" —
  // backend/src/progress/router.py's FileNotFoundError handler); QuizPlayer's
  // catch dispatches FAILED (#528).
  await page
    .getByRole("button", { name: /^Option /i })
    .first()
    .click();
  await page.getByRole("button", { name: /submit answer/i }).click();

  // The exact copy from QuizPlayer.tsx — not a generic truthy check.
  await expect(
    page.getByText("We couldn't save that answer. Check your connection and try again."),
  ).toBeVisible({ timeout: 15000 });

  // The button must offer a real retry, not stay dead on "Submit answer".
  await expect(page.getByRole("button", { name: /^try again$/i })).toBeVisible();

  // Whatever is shown must be student-safe: no status codes, no stack traces,
  // no internal error codes.
  const body = (await page.textContent("body")) ?? "";
  expect(body).not.toMatch(
    /traceback|FileNotFoundError|\/data\/content|500 Internal|quiz_not_found/i,
  );
});
