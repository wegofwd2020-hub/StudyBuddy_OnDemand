# Quiz Answer Review and Validation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A school reviewer can see every quiz question for a unit with its correct answer, mark it checked, and correct a wrong answer for their own school — live immediately, audited — even when the school reaches that curriculum only through a classroom package.

**Architecture:** One new RLS table for per-school validation state; three school-scoped endpoints (list / validate / correct) that reuse the existing override machinery (`import_unit_content`'s fork+import, `approve` with `publish=true`); one new page reached from the Unit Performance report, which gains the `curriculum_id` its rows currently lack.

**Tech Stack:** FastAPI + asyncpg (backend/src/school), Alembic (migration 0072), Next.js 15 + React Query (web/app/(school)), pytest in the `api` container, vitest on the host.

**Spec:** `docs/superpowers/specs/2026-09-17-quiz-answer-review-design.md` — read it first; it carries the four user decisions and the measured demo facts that shaped this.

## How the test steps are written (deviation, stated on purpose)

Task 1 carries literal test code. Tasks 2-5 specify each test as a named
assertion in a bullet list instead: the fixtures they need (a school, a fork, an
active override, two schools' feedback) already exist in
`backend/tests/test_quiz_fork_grading_529.py` and the reports suites, and copying
~400 lines of fixture code into this plan would be less accurate than pointing at
them. **Each bullet is one test**: name it after the bullet, write it FIRST, and
watch it fail for the stated reason before implementing. If a bullet cannot be
turned into a failing test, stop and say so rather than implementing blind.

## Global Constraints

- Branch `feat/762-quiz-answer-review` (already created, spec committed). Do not switch branches or create a worktree — the `api` container bind-mounts this checkout.
- Backend tests: `docker compose exec -T api python -m pytest <paths> -q --tb=short -p no:cacheprovider`. **Never** pass `-e TEST_DB_URL=` to pytest (pitfall #37). **Never** run two pytest sessions at once (pitfall #41).
- Frontend: run `npx vitest run`, `npx eslint`, `npx prettier --check .` from `web/`. For typecheck use `npx tsc --noEmit -p <scratchpad>/tsconfig.json` (excludes `.next`, pitfall #39) — NOT `npm run typecheck`.
- Any schema/response change ⇒ regenerate the API contract (`backend/scripts/export_openapi.py` → `npm run gen:types`) **and** hand-edit the DTO in `web/lib/api/*.ts` (pitfall #40 — those are hand-written).
- RLS: every new table gets `ENABLE` + `FORCE ROW LEVEL SECURITY` and a `tenant_isolation` policy on `school_id`, copying `0059_teacher_capabilities.py:67-77`.
- Capability guards come from `backend/src/school/capability_guards.py`: `require_curriculum_view` (read), `require_review` (write). `school_admin` is an implicit superset — do not special-case it.
- Lint/format backend with `ruff check` + `ruff format` (config `backend/pyproject.toml`, line-length 100).
- Never stage `data/content/` or `.playwright-mcp/`.
- Commits end with `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>`.

## Known traps in the code this touches

1. **Creating a fork repoints the grade.** `import_unit_content` (router.py:2203-2215) upserts `grade_curriculum_assignments` for the whole grade when it creates the fork. A "correct one answer" action therefore changes what that grade resolves to. The confirmation text in Task 5 must say so, and Task 4's test must assert it.
2. **`_assert_school_owns_curriculum`** (router.py:2339-2349) rejects platform curricula. The correct endpoint must resolve the school's fork FIRST and then operate on the fork's id, never the platform id.
3. **Serving and grading must agree** (#529). After a correction, assert the corrected answer through `resolve_quiz_answer_key`, not just in the table.
4. **`revert_unit_override` writes the active pointer on the wrong key** (#803). Do not copy that INSERT; copy `approve_unit_content`'s (router.py:3159-3167).

## File Structure

| File | Responsibility |
|---|---|
| `backend/alembic/versions/0072_question_validations.py` (create) | table + RLS |
| `backend/src/school/answer_review_service.py` (create) | list / validate / correct logic, ownership resolution |
| `backend/src/school/answer_review_router.py` (create) | 3 endpoints, guards, audit |
| `backend/src/school/schemas.py` (modify) | request/response models |
| `backend/src/reports/service.py` (modify) | add `curriculum_id` to Unit Performance rows |
| `backend/src/reports/schemas.py` (modify) | `CurriculumHealthUnit.curriculum_id` |
| `web/lib/api/answers.ts` (create) | client + hand-written DTOs |
| `web/app/(school)/school/content/[curriculum_id]/units/[unit_id]/answers/page.tsx` (create) | the page |
| `web/app/(school)/school/reports/units/page.tsx` (modify) | "Review answers" link per row |
| tests as listed per task | |

---

### Task 1: `question_validations` table

**Files:**
- Create: `backend/alembic/versions/0072_question_validations.py`
- Test: `backend/tests/test_question_validations_schema_762.py`

**Interfaces produced:** table `question_validations(school_id uuid, stable_question_id text, correct_text text, validated_by uuid, validated_at timestamptz)`, PK `(school_id, stable_question_id)`.

- [ ] **Step 1: Write the failing test**

```python
"""tests/test_question_validations_schema_762.py

Per-school "this answer was checked" state (#762). Keyed by stable_question_id
(ADR-008 / migration 0067) because `q1` names a SLOT within a set, not a
question, and the same question appears in several sets.
"""
import pytest


@pytest.mark.asyncio
async def test_the_table_exists_with_the_expected_key(db_conn):
    cols = {
        r["column_name"]: r["data_type"]
        for r in await db_conn.fetch(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_name = 'question_validations'"
        )
    }
    assert set(cols) == {
        "school_id", "stable_question_id", "correct_text", "validated_by", "validated_at",
    }
    pk = [
        r["attname"]
        for r in await db_conn.fetch(
            "SELECT a.attname FROM pg_index i "
            "JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey) "
            "WHERE i.indrelid = 'question_validations'::regclass AND i.indisprimary"
        )
    ]
    assert sorted(pk) == ["school_id", "stable_question_id"]


@pytest.mark.asyncio
async def test_row_level_security_is_forced(db_conn):
    row = await db_conn.fetchrow(
        "SELECT relrowsecurity, relforcerowsecurity FROM pg_class "
        "WHERE relname = 'question_validations'"
    )
    assert row["relrowsecurity"] and row["relforcerowsecurity"]
    policies = [
        r["polname"]
        for r in await db_conn.fetch(
            "SELECT polname FROM pg_policy WHERE polrelid = 'question_validations'::regclass"
        )
    ]
    assert "tenant_isolation" in policies
```

- [ ] **Step 2: Run it — expect failure**

`docker compose exec -T api python -m pytest tests/test_question_validations_schema_762.py -q --tb=short -p no:cacheprovider`
Expected: both fail (`assert set() == {...}`) because the table does not exist.

- [ ] **Step 3: Write the migration**

Copy the structure of `0059_teacher_capabilities.py` (revision chain: `down_revision = "0071"`, `revision = "0072"`). Table:

```python
op.execute("""
    CREATE TABLE IF NOT EXISTS question_validations (
        school_id           UUID        NOT NULL REFERENCES schools(school_id) ON DELETE CASCADE,
        stable_question_id  TEXT        NOT NULL,
        correct_text        TEXT        NOT NULL,
        validated_by        UUID        NOT NULL REFERENCES teachers(teacher_id),
        validated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
        PRIMARY KEY (school_id, stable_question_id)
    )
""")
op.execute(
    "CREATE INDEX IF NOT EXISTS ix_question_validations_school "
    "ON question_validations(school_id)"
)
```
then the three RLS statements copied verbatim from `0059_teacher_capabilities.py:67-77` with the table name swapped. `downgrade()` drops the table CASCADE.

- [ ] **Step 4: Run the test — expect pass.** Then `docker compose exec -e TEST_DB_URL= api alembic upgrade head` is NOT needed (pytest's fixture migrates the test DB); leave the dev DB alone for now.

- [ ] **Step 5: Lint and commit**

```bash
docker compose exec -T api ruff check alembic/versions/0072_question_validations.py tests/test_question_validations_schema_762.py
docker compose exec -T api ruff format alembic/versions/0072_question_validations.py tests/test_question_validations_schema_762.py
git add backend/alembic/versions/0072_question_validations.py backend/tests/test_question_validations_schema_762.py
git commit -m "feat(db): question_validations — per-school checked answers (#762)

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Listing a unit's answers

**Files:**
- Create: `backend/src/school/answer_review_service.py`, `backend/src/school/answer_review_router.py`
- Modify: `backend/src/school/schemas.py`, `backend/main.py` (register the router next to the other school routers)
- Test: `backend/tests/test_answer_review_list_762.py`

**Interfaces produced:**
- `list_unit_answers(conn, storage, redis, *, school_id, curriculum_id, unit_id, lang) -> dict` with
  `{"ownership": "none|fork|override", "serving_curriculum_id": str, "questions": [ {stable_question_id, set_number, question_id, question_text, options: [{option_id, text}], correct_option, validated: {by, at, stale} | None, flag_count} ]}`
- `GET /schools/{school_id}/content/{curriculum_id}/units/{unit_id}/answers?lang=en`

**Consumes:** `get_active_override`, `resolve_content_curriculum`, `_parse_quiz_answer_key`, `stable_question_id` (all existing, in `src/content/service.py` / `src/core/question_identity.py`).

- [ ] **Step 1: Write the failing tests** — `backend/tests/test_answer_review_list_762.py`, covering:
  - every question of all quiz sets present on disk is listed, each with its correct option and a `stable_question_id`;
  - `ownership` is `none` for a platform curriculum the school has not adopted (the demo's case), `override` when an active override exists, and the listed body is then the OVERRIDE's, not the store's;
  - `validated` is null before any validation, and `flag_count` counts only this school's students' `feedback` rows for that `stable_question_id` (seed two schools; assert no bleed);
  - a teacher of another school gets 403; a teacher of this school with no curriculum capability gets 403 (`require_curriculum_view`); a `school_admin` succeeds.
  Base the fixtures on `backend/tests/test_quiz_fork_grading_529.py` (school + fork + override) — read it first and reuse its helpers rather than inventing new ones.

- [ ] **Step 2: Run — expect ImportError** (`No module named 'src.school.answer_review_service'`).

- [ ] **Step 3: Implement the service.** Resolution order, mirroring serving exactly:
  1. resolve what the school owns: active override for (school, curriculum, unit, lang, `quiz_set_*`) → `override`; else a school fork whose `source_curriculum_id` = this curriculum → `fork`; else `none`;
  2. read each `quiz_set_{n}_{lang}.json` from the override body or, failing that, the content store under the OOB curriculum (`resolve_content_curriculum`);
  3. for each question compute `stable_question_id(curriculum_id, unit_id, lang, question_text)` using the SERVING curriculum id — the same input the grader uses, or the ids will not match what `progress_answers`/`feedback` recorded;
  4. left-join `question_validations` for this school; mark `stale = (correct_text != current correct option's normalised text)`;
  5. left-join the flag counts:
```sql
SELECT f.stable_question_id, COUNT(*) AS flags
FROM feedback f
JOIN school_enrolments se ON se.student_id = f.student_id AND se.school_id = $1
WHERE f.stable_question_id = ANY($2::text[])
GROUP BY 1
```

- [ ] **Step 4: Implement the endpoint** in `answer_review_router.py`: `require_curriculum_view(teacher, school_id, request)`, then `async with get_db(request) as conn:` (NOT `Depends(get_db)` — it is an `@asynccontextmanager`, Epic 15's bug). Register the router in `main.py` beside the other school routers.

- [ ] **Step 5: Run the tests — expect pass.** Then regenerate the contract and hand-edit the DTO (Global Constraints), and commit.

---

### Task 3: Marking an answer checked

**Files:**
- Modify: `backend/src/school/answer_review_service.py`, `answer_review_router.py`, `schemas.py`
- Test: `backend/tests/test_answer_review_validate_762.py`

**Interfaces produced:** `POST .../answers/{stable_question_id}/validate` → `{"validated_at": ..., "validated_by": ...}`; `validate_answer(conn, *, school_id, curriculum_id, unit_id, lang, stable_question_id, teacher_id)`.

- [ ] **Step 1: Write the failing tests:**
  - validating stores the row with the CURRENT correct option's normalised text, and the listing then reports `validated` with `stale: false`;
  - after the correct answer changes (simulate by writing a new active override), the same listing reports `stale: true` — **the point of storing the text**;
  - a second school validating the same `stable_question_id` does not touch the first school's row (both exist, independently);
  - a plain teacher is refused (`require_review`), a `curriculum.review` teacher and a `school_admin` succeed;
  - validating a `stable_question_id` that is not in this unit is a 404, not a silent insert;
  - an audit row is written (patch `write_audit_log` and assert `event_type="quiz_answer.validated"` with school, unit and question id).

- [ ] **Step 2: Run — expect failures** (405/404 on the route, no rows written).

- [ ] **Step 3: Implement.** Upsert `ON CONFLICT (school_id, stable_question_id) DO UPDATE SET correct_text, validated_by, validated_at = now()`. Guard: `require_review`. Resolve the question from the same listing path so an unknown id 404s. Audit via `write_audit_log` (`src/core/events.py`) — fire-and-forget, never awaited on the request path.

- [ ] **Step 4: Run — expect pass. Lint. Commit.**

---

### Task 4: Correcting an answer (the three ownership cases)

**Files:**
- Modify: `backend/src/school/answer_review_service.py`, `answer_review_router.py`, `schemas.py`
- Test: `backend/tests/test_answer_review_correct_762.py`

**Interfaces produced:** `POST .../answers/{stable_question_id}/correct` body `{correct_option: "C", confirm_fork: bool}` → `{"ownership_before": "none|fork|override", "created": {"adoption": bool, "fork": bool, "import": bool}, "override_id": str, "grade_repointed": bool}`.

- [ ] **Step 1: Write the failing tests.** The three cases, each ending with a GRADING assertion:
  - **override exists** → new version, approved+active, and `resolve_quiz_answer_key` now returns the new correct index for that question;
  - **fork but no override for this unit** → the unit is imported first, then as above;
  - **no adoption** (the demo's case) → `confirm_fork: false` is refused with a machine-readable reason (`fork_confirmation_required`) and **writes nothing** (assert no adoption/fork/override rows); with `confirm_fork: true` the adoption, fork and import are created exactly once, the answer is corrected, and **`grade_curriculum_assignments` for that grade now points at the fork** (trap 1 — assert it explicitly, because it is a side effect on every student of that grade);
  - a second correction in the same curriculum needs no `confirm_fork`;
  - correcting re-validates the question (row present, `stale: false`);
  - option letter not present in the question → 422, nothing written;
  - permissions: plain teacher refused, reviewer and school_admin allowed, other school refused;
  - audit row `quiz_answer.corrected` carries old and new correct text.

- [ ] **Step 2: Run — expect failures.**

- [ ] **Step 3: Implement**, reusing existing code rather than reimplementing it:
  - adoption: the same INSERT `adopt_curriculum` uses (router.py:1816…);
  - fork + import: call the existing import path (router.py:2120+) — extract it into a callable if needed, do NOT duplicate its SQL;
  - new override version: copy `save_draft`'s INSERT shape, then set `review_status='approved'` and upsert `unit_content_active_versions` **with `school_id`** exactly as `approve_unit_content` does (router.py:3159-3167; trap 4);
  - the whole correction runs in ONE `async with conn.transaction():` so a failure cannot leave a fork with no override.
  - The body written is the served quiz body with only that question's `correct_option` changed. Assert before writing that nothing else differs (same shape as `rebalance_quiz_options.py`'s `_verify`).

- [ ] **Step 4: Run — expect pass. Lint. Commit.**

---

### Task 5: The page, and the link that makes it reachable

**Files:**
- Modify: `backend/src/reports/service.py` + `backend/src/reports/schemas.py` (add `curriculum_id` to Unit Performance rows — the rows carry `unit_id`, `subject`, `grade`, `stream` but NOT the curriculum, so today there is nothing to link with)
- Create: `web/lib/api/answers.ts`, `web/app/(school)/school/content/[curriculum_id]/units/[unit_id]/answers/page.tsx`
- Modify: `web/app/(school)/school/reports/units/page.tsx`
- Test: `backend/tests/test_unit_performance_curriculum_id_762.py`, `web/tests/unit/answer-review-page-762.test.tsx`

- [ ] **Step 1: Backend test first** — every Unit Performance row carries the `curriculum_id` the unit was resolved under (the fork's id when the school has one, matching `_streams_by_unit`'s fork→source rule), red before the change.
- [ ] **Step 2: Implement** in `get_curriculum_health` on the same pass that resolves subject/grade/stream (service.py ~1537-1551). Regenerate the contract; hand-edit `CurriculumHealthUnit` in `web/lib/api/reports.ts`.
- [ ] **Step 3: Frontend tests first** (`answer-review-page-762.test.tsx`): questions render with the correct option marked; "Checked" shows who and when; a stale validation renders "Needs re-checking"; the Correct control is absent for a teacher without review capability; choosing a new correct option calls the API with that letter; when the response says a fork would be created, a confirmation naming the consequence ("your school keeps its own copy… platform updates will no longer reach it… this grade's curriculum will point at your copy") is shown BEFORE any call with `confirm_fork: true`; rows sort by flag count by default.
- [ ] **Step 4: Build the page and the client.** Follow the existing school page patterns (React Query, `schoolApi`). Dates through `@/lib/utils/date` (#759 lint rule bans locale formatting).
- [ ] **Step 5: Add the "Review answers" link** to each Unit Performance row, carrying that row's `curriculum_id` and `unit_id`. Test: the link's href contains both.
- [ ] **Step 6: Link from the unit editor too.** The spec promises both entry points: add a "Review answers" link on `web/app/(school)/school/content/[curriculum_id]/units/[unit_id]/edit/page.tsx` (schools that DO have adoptions reach units that way). Test: the link renders with both ids.
- [ ] **Step 7: Run full frontend checks** (vitest, tsc, eslint, prettier) and the backend reports tests. Lint. Commit.

---

### Task 6: Whole-feature verification and PR

- [ ] **Step 1: Cross-tenant sweep.** Run every new backend test file plus `tests/test_reports.py tests/test_quiz_fork_grading_529.py tests/test_progress_server_side_grading.py tests/test_content.py` — the grading and override suites this feature leans on.
- [ ] **Step 2: Full backend suite, alone** (`docker compose exec -T api python -m pytest -q --tb=short -p no:cacheprovider`). 0 failures.
- [ ] **Step 3: Full frontend suite** + tsc + eslint + prettier.
- [ ] **Step 4: Contract check** — `git diff web/openapi.json web/lib/api/types.gen.ts` shows only this feature's additions, and the hand-written DTOs match.
- [ ] **Step 5: Push and open the PR** with: what/why, the three ownership cases, the grade-repointing consequence stated plainly, the demo situation (no adopted curricula), test evidence, and a post-deploy checklist. Do NOT merge; do NOT run anything against the demo.
