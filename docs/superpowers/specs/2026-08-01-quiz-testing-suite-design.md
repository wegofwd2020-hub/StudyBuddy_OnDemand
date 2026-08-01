# Quiz Testing Suite — design

**Date:** 2026-08-01
**Status:** approved, pending implementation plan
**Motivation:** [#524](https://github.com/wegofwd2020-hub/StudyBuddy_OnDemand/issues/524)

---

## 1. Why

On 2026-07-31 a QA pass found that **"Submit answer" did nothing** for every
student. The session was opened with a hardcoded `curriculum_id: "default"`,
grading looked the answer key up under that id, found nothing, and returned 404;
the client swallowed the rejection and left a dead button.

Fifty-five quiz-related tests were passing at the time:

| Layer | Files | Tests |
|---|---|---|
| Backend | `test_progress.py`, `test_progress_server_side_grading.py` | 23 |
| Web unit | `quiz-page`, `quiz-player-scoring`, `quiz-state` | 32 |
| E2E | `student_flow.spec.ts` | 1 path |

All of them mock the network. The backend tests stub `get_quiz_answer_key` and
never assert what it is called with; the Playwright spec fulfils `/progress/*`
with fabricated 200s. The one seam that broke — *does the session's
`curriculum_id` resolve to a real path in the content store* — is precisely the
seam every layer removes.

The suite specified here exists to close that class of gap: it runs against a
**live local stack**, and it is **run explicitly** on every change to the quiz
path.

## 2. Scope

**In scope** — four assertion areas:

1. **Full journey** — login → resolve curriculum → serve quiz → answer every
   question → end session → score → history and stats reflect it.
2. **Anti-cheat invariants** — the guarantees #506 introduced, currently only
   asserted against mocks.
3. **Failure surfacing** — a legitimate grading failure 404s honestly *and* the
   player shows a message rather than a dead button.
4. **Content integrity** — a sweep of real on-disk content for quiz data that
   would grade students incorrectly.

**Explicitly out of scope.** This is a quiz suite, not a general safety net. It
would have caught #524. It would **not** have caught #522 (`/visuals` 500) or
#526 (alert thresholds) — different subsystems. Stating this now so its coverage
is not over-trusted later.

<!-- doc-audit:ignore -->
Also out of scope: wiring into CI (see §7), and the Kivy mobile client's quiz
behaviour.

## 3. Architecture

```
scripts/quiz_suite.sh              ← orchestrator; the only thing you run
.claude/commands/quiz-suite.md     ← /quiz-suite wraps the script
backend/quiz_suite/                ← API tier (pytest, marker: quiz_live)
  conftest.py · seed.py · test_journey.py · test_anticheat.py
  test_failure_surface.py · test_content_integrity.py
web/tests/e2e/quiz-suite/          ← browser tier (Playwright project: quiz-suite)
  quiz-journey.spec.ts · quiz-failure.spec.ts
```

`backend/quiz_suite/` is a **sibling** of `backend/tests/`, not a subdirectory
of it — deliberately. `backend/tests/conftest.py` defines a session-scoped
autouse fixture that ends in `command.downgrade(cfg, "base")`; living outside
`backend/tests/` means that conftest can never apply to this package, no
matter how pytest is invoked.

Execution order is strict: **seed → API tier → browser tier → teardown**, with
teardown in a shell `trap` so it runs on failure and on Ctrl-C.

Flags: `--api-only`, `--browser-only`, `--keep` (skip teardown for debugging),
`-v`.

### 3.1 The API tier runs inside the `api` container, with NO `TEST_DB_URL`

It needs the dev database, the content store at `/data/content`, and HTTP to the
running app — one process with all three. It is invoked with **no
`TEST_DB_URL` flag at all** — `seed.py` and the pytest run both read
`DATABASE_URL`, which is already the dev database inside the container.

This is the opposite of the alembic rule, and the two are easy to conflate:

- **Alembic commands** (`alembic upgrade head`, etc.) require `-e
  TEST_DB_URL=` — CLAUDE.md pitfall #34 — because without it the container's
  `TEST_DB_URL` wins and alembic silently migrates `studybuddy_test` instead
  of dev.
- **This suite's pytest invocation must NEVER receive `-e TEST_DB_URL=`.**
  `backend/tests/conftest.py`'s session-scoped autouse `run_migrations`
  fixture ends in `command.downgrade(cfg, "base")`. That fixture does not run
  for `backend/quiz_suite/` (it lives outside `backend/tests/`, see §3 above),
  but blanking `TEST_DB_URL` on any pytest invocation makes `backend/alembic/env.py`
  fall back to `DATABASE_URL` — the dev database — for anything that *does*
  trigger a downgrade. Treating "always pass `-e TEST_DB_URL=`" as a blanket
  pytest habit is exactly backwards for this suite and is what wiped the dev
  database on 2026-08-01.

### 3.2 It does not reuse `backend/tests/conftest.py`

That conftest builds an app instance bound to the test database — the opposite of
this suite's purpose. The quiz-suite conftest speaks HTTP to the already-running
`http://localhost:8000` and touches the dev database only to seed and tear down.

### 3.3 The browser tier registers no route mocks

A new Playwright project, so it cannot inherit `student_flow`'s stubs. It points
at the real web container and logs in through the real login page as the seeded
student.

## 4. Fixture and data flow

Deterministic IDs from a reserved block (`05000000-…`); no `uuid4()`, matching
the convention in `tests/helpers/token_factory.py`.

### 4.1 What is seeded

A throwaway school, **two students**, and a **school-owned** curriculum
`quizsuite-2026-g8` with **two units**:

| Entity | Purpose |
|---|---|
| `QS-TEST-001` | full content — lesson + 3 quiz sets. Journey, anti-cheat, browser-happy-path. |
| `QS-NOQUIZ-001` | lesson only, **no quiz files**. The failure-surfacing case (§5.3). |
| Student A | in the school. Every tier uses this one. |
| Student B | **no school**, grade 8. Used only for the fallback assertion in §5.1 and as the "other student" in the 403 check (§5.2). |

Two units matter: the failure case needs a unit whose quiz is genuinely absent,
and deleting `QS-TEST-001`'s quiz mid-run would break every other tier. Seeding
the absence is cleaner than removing a file and restoring it.

School-owned is deliberate: it resolves through step 1 of
`resolve_curriculum_id` and avoids the RESTRICTIVE write-guard on
`owner_type='platform'` rows, so the fixture needs no `app.current_school_id =
'bypass'` gymnastics (pitfall #28).

The student is seeded for **local auth** with `password_hash` set and
`first_login = FALSE`. With `first_login` true the portal bounces the browser
tier to `/school/change-password?required=1` and every UI assertion fails on a
redirect (pitfall #24).

### 4.2 Content on disk

For `QS-TEST-001`: three quiz sets, a lesson, and a `meta.json` under
`/data/content/curricula/quizsuite-2026-g8/QS-TEST-001/`. For `QS-NOQUIZ-001`: a
lesson and `meta.json` only — no quiz files at all.

Three properties of the `QS-TEST-001` content are deliberate:

- `meta.json` model is **not** `dev-placeholder`. `get_content_file` refuses that
  content outright (pitfall #36), so a careless fixture would 404 and read as a
  grading bug.
- Set 1 question 1 has `correct_option: "B"` with options ordered **C, B, A**. An
  implementation grading by alphabetical position gets it wrong; one matching
  `option_id` gets it right.
- The same `question_id` (`q1…q3`) has **different** correct answers in each set.
  This is what makes set-pinning falsifiable: grade a later answer against a
  re-read rotation pointer and the assertion fails (pitfall #35).

### 4.3 Handoff

`seed.py` writes `.fixture.json` — student email and password, unit and
curriculum ids, and the expected answer key per set. The API tier reads it; the
orchestrator copies it across for the browser tier. Gitignored.

### 4.4 Teardown

Removes the database rows (school, both students, curriculum, both units,
sessions, answers, lesson_views), the content directory, and the Redis keys
that are deterministic and would otherwise poison the next run: `cur:{student}`
and every other `*{student_id}*`-matching key (including `quiz_set:{student}:{unit}`)
for both students, `content:*` / `csv:*` for the fixture curriculum, and the
school-scoped keys under `school_scan_pattern(school_id)`.

**Not cleaned up, deliberately:** the session-keyed grading cache —
`quizscore:{session_id}` and `quizset:{session_id}` (see
`backend/src/core/cache_keys.py`). Teardown never learns every `session_id`
the suite created across the journey/anti-cheat runs, and it doesn't need to:
`session_id` is a fresh random UUID per session, so a leftover key can never
collide with — and therefore can never poison — a future run, and both keys
carry a 6-hour TTL (`_TALLY_TTL` in `backend/src/progress/service.py`) so they
self-expire regardless.

Seeding is delete-then-insert, so a crashed run — or a deliberate `--keep` —
never wedges the next one.

## 5. Assertions

### 5.1 Journey (API)

- The session's `curriculum_id` is `quizsuite-2026-g8` when the request body
  sends `"default"` **or omits the field** — the #524 regression, caught at the
  contract.
- Each answer's verdict matches the fixture key **for the set actually served**.
- The final score equals the number genuinely correct.
- The session in `/progress/student` carries a real subject and grade — **not**
  `subject="unknown", grade=0`. This was #524's silent second-order damage: no
  error, no 404, quiz sessions simply attributed to nothing. A suite checking
  only "did grading work" stays green through it. (`GET /analytics/student/me`
  exists but returns aggregate metrics, not a raw per-session subject/grade —
  it is not the right endpoint for this assertion, and the suite does not call
  it.)
- A second attempt serves a different set, and grading follows *that* set.
- Student B (no school, grade 8) opens a session and it resolves to
  `default-2026-g8`. This asserts the returned string, not content existence, so
  the fallback branch is covered without depending on any machine having G8
  content built. Student B never answers questions.

### 5.2 Anti-cheat (API)

- The served quiz body contains no `correct_option` / `correct_index` anywhere —
  asserted against the **raw response body**, not the parsed model, so a leak
  through an unmapped field cannot hide. Testing the model tests the serializer;
  testing the body tests the wire.
- A request carrying `correct: true` and `score: 99` changes nothing; the end
  score is the server's tally.
- Pinning: answer q1, re-fetch the quiz mid-session to force the rotation pointer
  forward, answer q2 — still graded against the pinned set.
- Another student's session → 403. Unknown session → 404. Unknown
  `question_id` → 400, **not** 500.

### 5.3 Failure surfacing

Run against `QS-NOQUIZ-001`, the unit seeded with a lesson but no quiz files:

- **API** — `POST …/answer` returns 404 with a non-technical message, no 500.
- **Browser** — the player renders that message and the button offers "Try
  again". It is not dead. This is the reported symptom asserted at the UI, and
  the half a pure-API suite cannot reach.

### 5.4 Content integrity (real content, not the fixture)

Sweeps every curriculum under `/data/content/curricula` that has quiz files:

- every set parses as JSON
- every question has `question_id`, `options`, `correct_option`
- every `correct_option` resolves to an `option_id` that exists in that
  question's own options

The last check is the sharp one. `get_quiz_answer_key` currently **skips**
questions whose `correct_option` names a missing option — so those questions
silently grade every student wrong. Output is a per-curriculum table. Zero
content on the box produces a loud skip **with a count**, never a silent pass.

### 5.5 Browser tier

Two specs only — the happy journey and the failure case. Deliberately small:
every browser assertion is a flake risk, and the API tier already covers the
contract. These exist to prove the button moves.

## 6. Failure output and diagnostics

**Preflight.** Verifies the `api` and `web` containers are up and `/healthz`
answers. If not, exits **2** with `./dev_start.sh` in the message.

This is the point of the design, not a nicety. A suite that cannot distinguish
"your code is broken" from "your stack isn't running" costs more than it saves —
on 2026-08-01 a local Playwright run failed three specs and required a
stash-and-rerun on a clean tree to establish the failures were environmental.

**Exit codes:** `0` pass · `1` genuine test failure · `2` environment problem.

**Output:** a per-tier table with timings. On failure it prints the response body
and the `correlation_id` the API stamps on every error — the fastest path from a
red test to the matching line in `docker compose logs api`.

**No sleeps.** Where waiting is unavoidable the suite polls with a timeout.

**It never asserts on `progress_answers` rows.** Those writes are fire-and-forget
through Celery and may not exist when the session ends — the same reason
`end_session` tallies Redis rather than counting the table (pitfall #35). Score
assertions go through the end-of-session response and the Redis tally. A suite
asserting on those rows would be flaky in a way that looks like a grading bug.

**Budget:** under 90 seconds total, so running it on every change is realistic
rather than aspirational.

## 7. CI stance

**Not wired into CI.** The requirement is explicit invocation, and CI has no live
stack.

Both exclusions are properties of the code rather than of anyone's memory:

- the `quiz_live` marker keeps the API tier out of `pytest -q`
- a separate Playwright project keeps the browser tier out of
  `npx playwright test`

Without the marker, CI would collect these tests with no stack up and fail every
PR.

Adding a compose-based CI job later is a separate decision. The suite should earn
trust locally first.

## 8. Acceptance criteria

<!-- doc-audit:ignore -->
1. `/quiz-suite` (or `scripts/quiz_suite.sh`) runs green against a healthy local
   stack in under 90 seconds.
2. Reverting the fix in PR #528 — restoring the hardcoded `"default"` — turns the
   suite **red**, in both the journey tier and the browser tier.
3. With containers down, the suite exits 2 with actionable instructions, not a
   test failure.
4. `pytest -q` and `npx playwright test` are both unaffected: neither collects
   the new tests.
5. Two consecutive runs both pass — teardown leaves no residue in the database,
   the content store, or Redis.
6. A deliberately corrupted `correct_option` in fixture content makes the
   integrity tier fail with the offending unit named.

## 9. Open questions

None blocking. Two deferred decisions, recorded so they are not rediscovered:

- Whether the integrity sweep should eventually run against the demo box's
  content as well as local. It needs credentials and read access to that
  filesystem; out of scope here.
- Whether a CI job is worth the compose-in-CI cost. Revisit once the suite has
  been in use for a few weeks.

## 10. Verification record

Acceptance criterion 2 exercised on 2026-08-01: reverting the #528 fix in
`backend/src/progress/router.py::start_session` — replacing the
`resolve_curriculum_id(...)` call with `curriculum_id = body.curriculum_id or
"default"` — turned the suite red on both tiers.

API tier (`docker compose exec -T api` pytest run inside `./scripts/quiz_suite.sh`):
9 of 23 tests failed — `test_client_claiming_correctness_is_ignored`,
`test_graded_set_is_pinned_for_the_session`,
`test_unknown_question_is_a_400_not_a_500` (all in `test_anticheat.py`),
`test_session_uses_the_resolved_curriculum_not_the_body`,
`test_session_without_curriculum_id_resolves`,
`test_unaffiliated_student_falls_back_to_default_package`,
`test_full_run_scores_what_the_student_earned`,
`test_session_is_attributed_to_a_real_subject_and_grade`,
`test_second_attempt_rotates_the_set_and_grades_against_it` (all in
`test_journey.py`) — `9 failed, 14 passed in 2.49s`.

Browser tier: 3 of 4 specs failed — "a grading failure mid-quiz shows the
failure message and 'Try again', not a dead button" (`quiz-failure.spec.ts`),
"submit reveals the verdict and advances to the next question" and
"completing the quiz reaches a result screen with a real score"
(`quiz-journey.spec.ts`) — `3 failed, 1 passed (1.4m)`.

`./scripts/quiz_suite.sh; echo "exit=$?"` → `exit=1`. This is a stronger
result than the acceptance criterion's minimum (2 API tests + 1 browser
spec) — the criterion is satisfied with margin.

Restoring the fix (`git checkout backend/src/progress/router.py`,
`docker compose restart api`) and re-running returned the suite to green:
23 API tests passed, 4 browser specs passed, `exit=0`.

Measured runtime (green run immediately following the restore): **36.7s**
wall clock (budget: 90s). A second green run beforehand (baseline, prior to
the revert) measured 27.3s — both comfortably within budget.
