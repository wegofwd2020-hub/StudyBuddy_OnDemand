# Quiz Testing Suite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an explicitly-invoked test suite that exercises the quiz path against a live local stack, so regressions like [#524](https://github.com/wegofwd2020-hub/StudyBuddy_OnDemand/issues/524) fail a test instead of reaching a QA pass.

**Architecture:** A shell orchestrator (`scripts/quiz_suite.sh`) runs seed → API tier → browser tier → teardown, with teardown in a `trap`. The API tier is pytest running *inside the `api` container* (it needs the dev DB, `/data/content`, and HTTP to the app in one process) and speaks HTTP to the already-running app rather than building its own app instance. The browser tier is a separate Playwright project with no route mocks. A hermetic fixture (2 students, 2 units, deterministic IDs) backs the behavioural tiers; the content-integrity tier sweeps real on-disk content.

**Tech Stack:** pytest + httpx + asyncpg (API tier), Playwright (browser tier), bash (orchestrator), Docker Compose.

**Spec:** `docs/superpowers/specs/2026-08-01-quiz-testing-suite-design.md`

## Global Constraints

Every task's requirements implicitly include these. They are all drawn from real defects in this repo.

- **NEVER pass `-e TEST_DB_URL=` to a `pytest` command. It destroys the dev database.**
  `backend/tests/conftest.py:102-121` defines `run_migrations` as
  `scope="session", autouse=True`, ending in `command.downgrade(cfg, "base")` —
  which drops every table. That is safe only because it normally targets
  `studybuddy_test`. Blanking `TEST_DB_URL` makes `alembic/env.py` fall back to
  `DATABASE_URL`, pointing the downgrade at the **dev** database. This happened
  on 2026-08-01 and wiped it.
  - The quiz suite lives at `backend/quiz_suite/` — **outside `backend/tests/`** —
    precisely so that root conftest never applies to it. Do not move it under
    `tests/`, and do not add a session-scoped migration fixture to it.
  - The quiz suite needs no flag at all: `seed.py` reads `DATABASE_URL`, which is
    already the dev database.
  - `-e TEST_DB_URL=` remains correct and REQUIRED for **alembic** commands
    (pitfall #34), which is the narrower claim CLAUDE.md actually makes.
- **After any schema rebuild, restart `api` and `pgbouncer`.** Pooled connections
  hold cached plans against dropped tables; without a restart the whole backend
  suite fails in ways that look like application bugs (446 spurious failures
  observed on 2026-08-01).
- **Every asyncpg connection in the seeder runs `SET app.current_school_id = 'bypass'` immediately after connecting.** RLS otherwise hides and rejects the rows (pitfalls #23, #28).
- **Deterministic IDs only.** Reserved block `q5000000-…`. Never `uuid4()` in fixtures.
- **`meta.json` `model` must NOT be `dev-placeholder`.** `get_content_file` refuses that content outright (pitfall #36).
- **Student passwords ≥12 characters, ≤72 bytes**, and seeded students have `first_login = FALSE` (pitfall #24).
- **Never assert on `progress_answers` rows.** Those writes are fire-and-forget Celery; assert via the end-of-session response instead (pitfall #35).
- **`curriculum_units` INSERT must include `unit_name`** (NOT NULL, pitfall #30).
- Total suite runtime target: **under 90 seconds**.
- Fixture constants live in exactly one place, `backend/quiz_suite/constants.py`, and are imported everywhere else.

---

## File Structure

| File | Responsibility |
|---|---|
| `backend/quiz_suite/__init__.py` | package marker |
| `backend/quiz_suite/constants.py` | all fixture IDs, emails, passwords, unit/curriculum names, expected answer keys |
| `backend/quiz_suite/seed.py` | seed + teardown + `.fixture.json` writer; runnable as `python -m quiz_suite.seed {seed,teardown}` |
| `backend/quiz_suite/conftest.py` | HTTP client fixtures + student tokens; does NOT import the app |
| `backend/quiz_suite/test_journey.py` | §5.1 assertions |
| `backend/quiz_suite/test_anticheat.py` | §5.2 assertions |
| `backend/quiz_suite/test_failure_surface.py` | §5.3 API half |
| `backend/quiz_suite/test_content_integrity.py` | §5.4 sweep over real content |
| `backend/setup.cfg` | register `quiz_live` marker; exclude it from the default run |
| `web/tests/e2e/quiz-suite/quiz-journey.spec.ts` | §5.3/§5.5 browser happy path |
| `web/tests/e2e/quiz-suite/quiz-failure.spec.ts` | §5.3 browser failure case |
| `web/playwright.config.ts` | env-gated `quiz-suite` project |
| `scripts/quiz_suite.sh` | orchestrator + preflight + result table |
| `.claude/commands/quiz-suite.md` | `/quiz-suite` slash command |
| `.gitignore` | ignore `.fixture.json` |

---

### Task 1: Marker plumbing + package skeleton + HTTP conftest

Deliverable: `pytest -m quiz_live` inside the container runs a connectivity check against the live app; a plain `pytest -q` does not collect it.

**Files:**
- Create: `backend/quiz_suite/__init__.py`, `backend/quiz_suite/constants.py`, `backend/quiz_suite/conftest.py`, `backend/quiz_suite/test_smoke.py`
- Modify: `backend/setup.cfg`

**Interfaces:**
- Consumes: nothing.
- Produces: `constants.API_BASE: str`, `constants.FIXTURE_PATH: str`, `constants.SCHOOL_ID/STUDENT_A_ID/STUDENT_B_ID/CURRICULUM_ID/UNIT_QUIZ/UNIT_NOQUIZ: str`, `constants.STUDENT_A_EMAIL/STUDENT_B_EMAIL/STUDENT_PASSWORD: str`; conftest fixture `api: httpx.AsyncClient`.

- [ ] **Step 1: Register the marker and exclude it by default**

In `backend/setup.cfg`, under `[tool:pytest]`, change the `addopts` line and add a `markers` block:

```ini
addopts = -v --tb=short -m "not quiz_live"
markers =
    quiz_live: live-stack quiz suite; requires a running dev stack. Run via scripts/quiz_suite.sh.
```

- [ ] **Step 2: Create the constants module**

Create `backend/quiz_suite/__init__.py` as an empty file, then `backend/quiz_suite/constants.py`:

```python
"""
Fixture identity for the live quiz suite.

Every id is deterministic (reserved q5000000- block) so a crashed run can always
be cleaned up by re-running teardown. Nothing here is used outside the suite.
"""

from __future__ import annotations

# The suite runs INSIDE the api container, so the app is on localhost.
API_BASE = "http://localhost:8000/api/v1"

CONTENT_ROOT = "/data/content/curricula"
FIXTURE_PATH = "/app/quiz_suite/.fixture.json"

SCHOOL_ID = "q5000000-0000-0000-0000-000000000001"
STUDENT_A_ID = "q5000000-0000-0000-0000-00000000000a"
STUDENT_B_ID = "q5000000-0000-0000-0000-00000000000b"

CURRICULUM_ID = "quizsuite-2026-g8"
UNIT_QUIZ = "QS-TEST-001"
UNIT_NOQUIZ = "QS-NOQUIZ-001"
GRADE = 8
YEAR = 2026
SUBJECT = "Science"

STUDENT_A_EMAIL = "quizsuite-a@test.invalid"
STUDENT_B_EMAIL = "quizsuite-b@test.invalid"
# >= 12 chars, <= 72 bytes (bcrypt limit).
STUDENT_PASSWORD = "QuizSuite-Fixture-2026"
```

- [ ] **Step 3: Create the conftest**

Create `backend/quiz_suite/conftest.py`:

```python
"""
Fixtures for the live quiz suite.

Deliberately does NOT import the FastAPI app or reuse backend/tests/conftest.py:
that conftest builds an app bound to studybuddy_test, which is the opposite of
what this suite tests. Here we speak HTTP to the already-running app.
"""

from __future__ import annotations

import json
import os

import httpx
import pytest
import pytest_asyncio

from quiz_suite import constants as C


@pytest_asyncio.fixture
async def api():
    async with httpx.AsyncClient(base_url=C.API_BASE, timeout=20.0) as client:
        yield client


@pytest.fixture(scope="session")
def fixture_data() -> dict:
    """The handoff file written by seed.py. Fails loudly if the seed never ran."""
    if not os.path.exists(C.FIXTURE_PATH):
        pytest.fail(
            f"{C.FIXTURE_PATH} missing — run scripts/quiz_suite.sh, which seeds first."
        )
    with open(C.FIXTURE_PATH) as fh:
        return json.load(fh)


async def login(client: httpx.AsyncClient, email: str, password: str) -> str:
    """Return a student JWT. The login response field is `token`, not `access_token`."""
    r = await client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text}"
    body = r.json()
    return body.get("token") or body["access_token"]


@pytest_asyncio.fixture
async def token_a(api) -> str:
    return await login(api, C.STUDENT_A_EMAIL, C.STUDENT_PASSWORD)


@pytest_asyncio.fixture
async def token_b(api) -> str:
    return await login(api, C.STUDENT_B_EMAIL, C.STUDENT_PASSWORD)


@pytest.fixture
def auth_a(token_a) -> dict:
    return {"Authorization": f"Bearer {token_a}"}


@pytest.fixture
def auth_b(token_b) -> dict:
    return {"Authorization": f"Bearer {token_b}"}
```

- [ ] **Step 4: Write the failing connectivity test**

Create `backend/quiz_suite/test_smoke.py`:

```python
"""Proves the suite can reach the live app before any other tier is trusted."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.quiz_live


@pytest.mark.asyncio
async def test_live_app_is_reachable(api):
    r = await api.get("/healthz")
    assert r.status_code == 200, f"live stack not reachable: {r.status_code}"
```

- [ ] **Step 5: Verify the default run does NOT collect it**

Run:
```bash
docker compose exec -T api python -m pytest quiz_suite -q
```
Expected: `no tests ran` / all deselected — the `-m "not quiz_live"` in `addopts` filters them out.

- [ ] **Step 6: Verify the explicit run DOES collect and pass it**

Run:
```bash
docker compose exec -T api python -m pytest quiz_suite -m quiz_live -q
```
Expected: PASS (1 test).

- [ ] **Step 7: Confirm the existing suite is unaffected**

Run:
```bash
docker compose exec -T api python -m pytest -q 2>&1 | tail -3
```
Expected: same totals as before this task (1178 passed, 2 skipped).

- [ ] **Step 8: Commit**

```bash
git add backend/setup.cfg backend/quiz_suite/
git commit -m "test(quiz-suite): package skeleton, quiz_live marker, live HTTP conftest"
```

---

### Task 2: Seeder and teardown

Deliverable: `python -m quiz_suite.seed seed` creates the fixture and writes `.fixture.json`; `teardown` removes every trace; a test proves login works after seed.

**Files:**
- Create: `backend/quiz_suite/seed.py`, `backend/quiz_suite/test_fixture.py`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: `constants` from Task 1.
- Produces: `seed.seed() -> dict`, `seed.teardown() -> None`, and `.fixture.json` with keys `student_a_email`, `student_b_email`, `password`, `curriculum_id`, `unit_quiz`, `unit_noquiz`, `answer_key` (`{set_number: {question_id: correct_index}}`).

- [ ] **Step 1: Write the seeder**

Create `backend/quiz_suite/seed.py`:

```python
"""
Seed and tear down the hermetic quiz-suite fixture.

Run inside the api container:
    python -m quiz_suite.seed seed
    python -m quiz_suite.seed teardown

Seeding is delete-then-insert, so a crashed run never wedges the next one.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import sys
from datetime import datetime, timezone

import asyncpg
import bcrypt

from quiz_suite import constants as C

# ── Quiz content ──────────────────────────────────────────────────────────────
# Two traps are deliberate:
#  1. q1's correct option is "B" but B sits at position 0 — a grader keying off
#     alphabetical position gets it wrong.
#  2. The same question_id has a DIFFERENT correct option in each set, so
#     grading a later answer against a re-read rotation pointer fails loudly.
_SET_ANSWERS = {
    1: {"q1": "B", "q2": "A", "q3": "C"},
    2: {"q1": "A", "q2": "C", "q3": "B"},
    3: {"q1": "C", "q2": "B", "q3": "A"},
}
# Option order is fixed and NOT alphabetical.
_OPTION_ORDER = ["B", "C", "A"]


def _build_quiz_set(set_number: int) -> dict:
    questions = []
    for qid, correct in _SET_ANSWERS[set_number].items():
        questions.append(
            {
                "question_id": qid,
                "question_text": f"Quiz-suite {qid}, set {set_number}?",
                "question_type": "multiple_choice",
                "options": [
                    {"option_id": oid, "text": f"Option {oid}"} for oid in _OPTION_ORDER
                ],
                "correct_option": correct,
                "explanation": f"{correct} is correct in set {set_number}.",
                "difficulty": "easy",
            }
        )
    return {"unit_id": C.UNIT_QUIZ, "set_number": set_number, "questions": questions}


def expected_answer_key() -> dict:
    """{set_number: {question_id: correct_index}} — index within _OPTION_ORDER."""
    return {
        str(s): {qid: _OPTION_ORDER.index(opt) for qid, opt in answers.items()}
        for s, answers in _SET_ANSWERS.items()
    }


def _lesson(unit_id: str) -> dict:
    return {
        "unit_id": unit_id,
        "title": f"Quiz suite lesson for {unit_id}",
        "sections": [
            {"heading": "Introduction", "body": "Fixture lesson body."},
            {"heading": "Summary", "body": "Fixture lesson summary."},
        ],
        "key_points": ["Fixture key point."],
    }


def _meta() -> dict:
    # model must NOT be "dev-placeholder" — get_content_file refuses that content.
    return {
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "model": "quiz-suite-fixture",
        "content_version": 1,
        "langs_built": ["en"],
    }


def _write_content() -> None:
    quiz_dir = os.path.join(C.CONTENT_ROOT, C.CURRICULUM_ID, C.UNIT_QUIZ)
    noquiz_dir = os.path.join(C.CONTENT_ROOT, C.CURRICULUM_ID, C.UNIT_NOQUIZ)
    os.makedirs(quiz_dir, exist_ok=True)
    os.makedirs(noquiz_dir, exist_ok=True)

    for set_number in (1, 2, 3):
        path = os.path.join(quiz_dir, f"quiz_set_{set_number}_en.json")
        with open(path, "w") as fh:
            json.dump(_build_quiz_set(set_number), fh)

    for unit_id, directory in ((C.UNIT_QUIZ, quiz_dir), (C.UNIT_NOQUIZ, noquiz_dir)):
        with open(os.path.join(directory, "lesson_en.json"), "w") as fh:
            json.dump(_lesson(unit_id), fh)
        with open(os.path.join(directory, "meta.json"), "w") as fh:
            json.dump(_meta(), fh)
    # UNIT_NOQUIZ deliberately gets NO quiz files — that absence is the fixture
    # for the failure-surfacing tier.


async def _connect() -> asyncpg.Connection:
    dsn = os.environ["DATABASE_URL"]
    conn = await asyncpg.connect(dsn)
    # RLS hides/refuses these rows without this (pitfalls #23, #28).
    await conn.execute("SET app.current_school_id = 'bypass'")
    return conn


async def _delete_rows(conn: asyncpg.Connection) -> None:
    for sid in (C.STUDENT_A_ID, C.STUDENT_B_ID):
        await conn.execute("DELETE FROM progress_answers WHERE session_id IN "
                           "(SELECT session_id FROM progress_sessions WHERE student_id = $1)", sid)
        await conn.execute("DELETE FROM progress_sessions WHERE student_id = $1", sid)
        await conn.execute("DELETE FROM lesson_views WHERE student_id = $1", sid)
        await conn.execute("DELETE FROM students WHERE student_id = $1", sid)
    await conn.execute("DELETE FROM curriculum_units WHERE curriculum_id = $1", C.CURRICULUM_ID)
    await conn.execute("DELETE FROM curricula WHERE curriculum_id = $1", C.CURRICULUM_ID)
    await conn.execute("DELETE FROM schools WHERE school_id = $1", C.SCHOOL_ID)


async def _seed_rows(conn: asyncpg.Connection, password_hash: str) -> None:
    await conn.execute(
        "INSERT INTO schools (school_id, name, contact_email, country, status) "
        "VALUES ($1, $2, $3, 'CA', 'active')",
        C.SCHOOL_ID, "Quiz Suite Fixture School", "quizsuite-school@test.invalid",
    )
    await conn.execute(
        "INSERT INTO curricula (curriculum_id, grade, year, name, is_default, school_id, "
        "owner_type, source_type, status) "
        "VALUES ($1, $2, $3, $4, FALSE, $5, 'school', 'default', 'active')",
        C.CURRICULUM_ID, C.GRADE, C.YEAR, "Quiz Suite Fixture Curriculum", C.SCHOOL_ID,
    )
    for unit_id, title in ((C.UNIT_QUIZ, "Quiz Suite Unit"), (C.UNIT_NOQUIZ, "Quiz Suite No-Quiz Unit")):
        # unit_name is NOT NULL — omitting it fails the insert (pitfall #30).
        await conn.execute(
            "INSERT INTO curriculum_units (unit_id, curriculum_id, subject, title, unit_name, "
            "sort_order, sequence, content_status) VALUES ($1, $2, $3, $4, $4, 1, 1, 'published')",
            unit_id, C.CURRICULUM_ID, C.SUBJECT, title,
        )
    # Student A is in the school (resolves via step 1 of resolve_curriculum_id).
    await conn.execute(
        "INSERT INTO students (student_id, external_auth_id, auth_provider, name, email, grade, "
        "locale, account_status, school_id, password_hash, first_login) "
        "VALUES ($1, $2, 'local', $3, $4, $5, 'en', 'active', $6, $7, FALSE)",
        C.STUDENT_A_ID, f"local|{C.STUDENT_A_EMAIL}", "Quiz Suite Student A",
        C.STUDENT_A_EMAIL, C.GRADE, C.SCHOOL_ID, password_hash,
    )
    # Student B has NO school — used only for the default-curriculum fallback
    # assertion and as the "other student" in the 403 check.
    await conn.execute(
        "INSERT INTO students (student_id, external_auth_id, auth_provider, name, email, grade, "
        "locale, account_status, school_id, password_hash, first_login) "
        "VALUES ($1, $2, 'local', $3, $4, $5, 'en', 'active', NULL, $6, FALSE)",
        C.STUDENT_B_ID, f"local|{C.STUDENT_B_EMAIL}", "Quiz Suite Student B",
        C.STUDENT_B_EMAIL, C.GRADE, password_hash,
    )


async def seed() -> dict:
    password_hash = bcrypt.hashpw(C.STUDENT_PASSWORD.encode(), bcrypt.gensalt(rounds=12)).decode()
    conn = await _connect()
    try:
        await _delete_rows(conn)
        await _seed_rows(conn, password_hash)
    finally:
        await conn.close()

    _write_content()

    data = {
        "student_a_email": C.STUDENT_A_EMAIL,
        "student_b_email": C.STUDENT_B_EMAIL,
        "password": C.STUDENT_PASSWORD,
        "curriculum_id": C.CURRICULUM_ID,
        "unit_quiz": C.UNIT_QUIZ,
        "unit_noquiz": C.UNIT_NOQUIZ,
        "answer_key": expected_answer_key(),
    }
    with open(C.FIXTURE_PATH, "w") as fh:
        json.dump(data, fh, indent=2)
    return data


async def _flush_redis() -> None:
    """Stale cur:/quiz_set: keys would poison the next run."""
    import redis.asyncio as aioredis

    client = aioredis.from_url(os.environ.get("REDIS_URL", "redis://redis:6379/0"))
    try:
        patterns = [
            f"cur:{C.STUDENT_A_ID}*", f"cur:{C.STUDENT_B_ID}*",
            f"*{C.STUDENT_A_ID}*", f"*{C.STUDENT_B_ID}*",
            f"content:{C.CURRICULUM_ID}*", f"csv:{C.CURRICULUM_ID}*",
        ]
        for pattern in patterns:
            async for key in client.scan_iter(match=pattern):
                await client.delete(key)
    finally:
        await client.aclose()


async def teardown() -> None:
    conn = await _connect()
    try:
        await _delete_rows(conn)
    finally:
        await conn.close()
    shutil.rmtree(os.path.join(C.CONTENT_ROOT, C.CURRICULUM_ID), ignore_errors=True)
    await _flush_redis()
    if os.path.exists(C.FIXTURE_PATH):
        os.remove(C.FIXTURE_PATH)


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "seed"
    if command == "seed":
        asyncio.run(seed())
        print("quiz-suite fixture seeded")
    elif command == "teardown":
        asyncio.run(teardown())
        print("quiz-suite fixture torn down")
    else:
        print(f"unknown command: {command}", file=sys.stderr)
        sys.exit(2)
```

- [ ] **Step 2: Write the failing fixture test**

Create `backend/quiz_suite/test_fixture.py`:

```python
"""The fixture must produce a student who can actually log in and see content."""

from __future__ import annotations

import pytest

from quiz_suite import constants as C

pytestmark = pytest.mark.quiz_live


@pytest.mark.asyncio
async def test_seeded_student_can_log_in(auth_a):
    assert auth_a["Authorization"].startswith("Bearer ey")


@pytest.mark.asyncio
async def test_seeded_unit_serves_a_quiz(api, auth_a):
    r = await api.get(f"/content/{C.UNIT_QUIZ}/quiz", headers=auth_a)
    assert r.status_code == 200, r.text
    assert len(r.json()["questions"]) == 3


@pytest.mark.asyncio
async def test_fixture_file_records_the_answer_key(fixture_data):
    assert set(fixture_data["answer_key"]) == {"1", "2", "3"}
    # q1 is correct option "B", which sits at index 0 — the alphabetical trap.
    assert fixture_data["answer_key"]["1"]["q1"] == 0
```

- [ ] **Step 3: Run it and watch it fail**

Run:
```bash
docker compose exec -T api python -m pytest quiz_suite/test_fixture.py -m quiz_live -q
```
Expected: FAIL — `.fixture.json` missing, login 401.

- [ ] **Step 4: Seed, then re-run**

Run:
```bash
docker compose exec -T api python -m quiz_suite.seed seed
docker compose exec -T api python -m pytest quiz_suite/test_fixture.py -m quiz_live -q
```
Expected: 3 PASS.

- [ ] **Step 5: Verify teardown is complete**

Run:
```bash
docker compose exec -T api python -m quiz_suite.seed teardown
docker compose exec -T api python -m pytest quiz_suite/test_fixture.py -m quiz_live -q
```
Expected: FAIL again (fixture gone). Then seed once more and confirm PASS — this proves seed is repeatable.

- [ ] **Step 6: Ignore the handoff file**

Append to `.gitignore`:
```
backend/quiz_suite/.fixture.json
web/tests/e2e/quiz-suite/.fixture.json
```

- [ ] **Step 7: Commit**

```bash
git add backend/quiz_suite/ .gitignore
git commit -m "test(quiz-suite): hermetic seeder and teardown with deterministic fixture"
```

---

### Task 3: Journey tier

Deliverable: the full student path asserted end to end, including the #524 regression.

**Files:**
- Create: `backend/quiz_suite/test_journey.py`

**Interfaces:**
- Consumes: `conftest.api/auth_a/auth_b/fixture_data`, `constants`.
- Produces: helper `answer_all(api, headers, session_id, key_for_set) -> list[dict]` used by Task 4.

- [ ] **Step 1: Write the journey tests**

Create `backend/quiz_suite/test_journey.py`:

```python
"""
The path a student actually walks. This is the tier that would have failed on
#524: the session's curriculum_id must be the RESOLVED one, or grading 404s.
"""

from __future__ import annotations

import pytest

from quiz_suite import constants as C

pytestmark = pytest.mark.quiz_live


async def start_session(api, headers, unit_id=C.UNIT_QUIZ, body=None):
    r = await api.post("/progress/session", json=body or {"unit_id": unit_id}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


async def serve_quiz(api, headers, unit_id=C.UNIT_QUIZ) -> dict:
    r = await api.get(f"/content/{unit_id}/quiz", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


async def answer_all(api, headers, session_id, key_for_set) -> list[dict]:
    """Answer q1..q3 correctly per the fixture key. Returns the server verdicts."""
    verdicts = []
    for qid, correct_index in key_for_set.items():
        r = await api.post(
            f"/progress/session/{session_id}/answer",
            json={"question_id": qid, "student_answer": correct_index, "ms_taken": 10},
            headers=headers,
        )
        assert r.status_code == 200, f"{qid}: {r.status_code} {r.text}"
        verdicts.append(r.json())
    return verdicts


@pytest.mark.asyncio
async def test_session_uses_the_resolved_curriculum_not_the_body(api, auth_a):
    """#524: a lying body must not decide what grading looks up."""
    session = await start_session(api, auth_a, body={"unit_id": C.UNIT_QUIZ, "curriculum_id": "default"})
    assert session["curriculum_id"] == C.CURRICULUM_ID


@pytest.mark.asyncio
async def test_session_without_curriculum_id_resolves(api, auth_a):
    session = await start_session(api, auth_a)
    assert session["curriculum_id"] == C.CURRICULUM_ID


@pytest.mark.asyncio
async def test_unaffiliated_student_falls_back_to_default_package(api, auth_b):
    """Student B has no school. Asserts the id string, not that content exists."""
    session = await start_session(api, auth_b)
    assert session["curriculum_id"] == f"default-{C.YEAR}-g{C.GRADE}"


@pytest.mark.asyncio
async def test_full_run_scores_what_the_student_earned(api, auth_a, fixture_data):
    quiz = await serve_quiz(api, auth_a)
    key = fixture_data["answer_key"][str(quiz["set_number"])]
    session = await start_session(api, auth_a)

    verdicts = await answer_all(api, auth_a, session["session_id"], key)
    assert all(v["correct"] for v in verdicts), verdicts

    r = await api.post(f"/progress/session/{session['session_id']}/end", json={}, headers=auth_a)
    assert r.status_code == 200, r.text
    result = r.json()
    assert result["score"] == len(key)
    assert result["total_questions"] == len(key)
    assert result["passed"] is True


@pytest.mark.asyncio
async def test_session_is_attributed_to_a_real_subject_and_grade(api, auth_a, fixture_data):
    """
    #524's silent second-order damage: sessions were written with grade=0 and
    subject="unknown" because create_session looked the unit up under "default".
    No error, no 404 — analytics simply attributed every quiz to nothing.
    """
    quiz = await serve_quiz(api, auth_a)
    key = fixture_data["answer_key"][str(quiz["set_number"])]
    session = await start_session(api, auth_a)
    await answer_all(api, auth_a, session["session_id"], key)
    await api.post(f"/progress/session/{session['session_id']}/end", json={}, headers=auth_a)

    r = await api.get("/progress/student", headers=auth_a)
    assert r.status_code == 200, r.text
    rows = [s for s in r.json()["sessions"] if s["unit_id"] == C.UNIT_QUIZ]
    assert rows, "the completed session is missing from history"
    assert rows[0].get("subject") not in (None, "", "unknown")
    assert rows[0].get("grade") not in (None, 0)


@pytest.mark.asyncio
async def test_second_attempt_rotates_the_set_and_grades_against_it(api, auth_a, fixture_data):
    first = await serve_quiz(api, auth_a)
    second = await serve_quiz(api, auth_a)
    assert first["set_number"] != second["set_number"], "rotation did not advance"

    session = await start_session(api, auth_a)
    key = fixture_data["answer_key"][str(second["set_number"])]
    verdicts = await answer_all(api, auth_a, session["session_id"], key)
    assert all(v["correct"] for v in verdicts), "graded against the wrong set"
```

- [ ] **Step 2: Run and confirm all pass**

Run:
```bash
docker compose exec -T api python -m quiz_suite.seed seed
docker compose exec -T api python -m pytest quiz_suite/test_journey.py -m quiz_live -q
```
Expected: 6 PASS. If `test_session_is_attributed_to_a_real_subject_and_grade` fails on a missing `subject`/`grade` key rather than a bad value, inspect the actual `/progress/student` response shape and assert on the fields it really returns — do not weaken the assertion to make it pass.

- [ ] **Step 3: Prove the tier catches #524**

Temporarily re-break the code: in `backend/src/progress/router.py::start_session`, replace the resolver call with `curriculum_id = body.curriculum_id or "default"`. Restart: `docker compose restart api`. Re-run the journey tier.
Expected: `test_session_uses_the_resolved_curriculum_not_the_body` and `test_full_run_scores_what_the_student_earned` FAIL. Then revert the edit and restart again; confirm green.

- [ ] **Step 4: Commit**

```bash
git add backend/quiz_suite/test_journey.py
git commit -m "test(quiz-suite): journey tier — resolved curriculum, scoring, attribution, rotation"
```

---

### Task 4: Anti-cheat tier

Deliverable: #506's guarantees asserted against the live stack rather than mocks.

**Files:**
- Create: `backend/quiz_suite/test_anticheat.py`

**Interfaces:**
- Consumes: `test_journey.start_session/serve_quiz/answer_all`, `conftest` fixtures.
- Produces: nothing consumed later.

- [ ] **Step 1: Write the anti-cheat tests**

Create `backend/quiz_suite/test_anticheat.py`:

```python
"""
The guarantees #506 introduced, asserted against the running app.

The existing backend tests assert these against a stubbed answer key, which is
how #524 slipped through — the stub is the thing that hides the bug.
"""

from __future__ import annotations

import pytest

from quiz_suite import constants as C
from quiz_suite.test_journey import answer_all, serve_quiz, start_session

pytestmark = pytest.mark.quiz_live


@pytest.mark.asyncio
async def test_served_quiz_leaks_no_answer_key(api, auth_a):
    """
    Asserted on the RAW body, not the parsed model. Testing the model tests the
    serializer; testing the body tests the wire.
    """
    r = await api.get(f"/content/{C.UNIT_QUIZ}/quiz", headers=auth_a)
    assert r.status_code == 200
    raw = r.text
    for forbidden in ("correct_option", "correct_index", "correct_answer"):
        assert forbidden not in raw, f"{forbidden} leaked in the served quiz"


@pytest.mark.asyncio
async def test_client_claiming_correctness_is_ignored(api, auth_a, fixture_data):
    quiz = await serve_quiz(api, auth_a)
    key = fixture_data["answer_key"][str(quiz["set_number"])]
    session = await start_session(api, auth_a)

    wrong_index = (key["q1"] + 1) % 3
    r = await api.post(
        f"/progress/session/{session['session_id']}/answer",
        json={
            "question_id": "q1",
            "student_answer": wrong_index,
            "correct": True,       # ignored
            "correct_answer": wrong_index,  # ignored
            "ms_taken": 10,
        },
        headers=auth_a,
    )
    assert r.status_code == 200, r.text
    assert r.json()["correct"] is False, "the server took the client's word for it"


@pytest.mark.asyncio
async def test_client_cannot_post_its_own_score(api, auth_a, fixture_data):
    quiz = await serve_quiz(api, auth_a)
    key = fixture_data["answer_key"][str(quiz["set_number"])]
    session = await start_session(api, auth_a)

    for qid, correct_index in key.items():
        await api.post(
            f"/progress/session/{session['session_id']}/answer",
            json={"question_id": qid, "student_answer": (correct_index + 1) % 3, "ms_taken": 10},
            headers=auth_a,
        )
    r = await api.post(
        f"/progress/session/{session['session_id']}/end",
        json={"score": 99, "total_questions": 99},
        headers=auth_a,
    )
    assert r.status_code == 200, r.text
    assert r.json()["score"] == 0


@pytest.mark.asyncio
async def test_graded_set_is_pinned_for_the_session(api, auth_a, fixture_data):
    """
    Answer q1, force the rotation pointer forward by re-fetching the quiz, then
    answer q2. Both must be graded against the set pinned at session start —
    the sets have different answers, so a re-read pointer fails here.
    """
    quiz = await serve_quiz(api, auth_a)
    pinned = str(quiz["set_number"])
    key = fixture_data["answer_key"][pinned]
    session = await start_session(api, auth_a)

    r = await api.post(
        f"/progress/session/{session['session_id']}/answer",
        json={"question_id": "q1", "student_answer": key["q1"], "ms_taken": 10},
        headers=auth_a,
    )
    assert r.json()["correct"] is True

    await serve_quiz(api, auth_a)  # advances the per-unit rotation pointer

    r = await api.post(
        f"/progress/session/{session['session_id']}/answer",
        json={"question_id": "q2", "student_answer": key["q2"], "ms_taken": 10},
        headers=auth_a,
    )
    assert r.status_code == 200, r.text
    assert r.json()["correct"] is True, "later answer was graded against a different set"


@pytest.mark.asyncio
async def test_another_students_session_is_forbidden(api, auth_a, auth_b):
    session = await start_session(api, auth_a)
    r = await api.post(
        f"/progress/session/{session['session_id']}/answer",
        json={"question_id": "q1", "student_answer": 0, "ms_taken": 10},
        headers=auth_b,
    )
    assert r.status_code == 403, r.text


@pytest.mark.asyncio
async def test_unknown_question_is_a_400_not_a_500(api, auth_a):
    session = await start_session(api, auth_a)
    r = await api.post(
        f"/progress/session/{session['session_id']}/answer",
        json={"question_id": "does-not-exist", "student_answer": 0, "ms_taken": 10},
        headers=auth_a,
    )
    assert r.status_code == 400, r.text
```

- [ ] **Step 2: Run**

Run:
```bash
docker compose exec -T api python -m pytest quiz_suite/test_anticheat.py -m quiz_live -q
```
Expected: 6 PASS.

- [ ] **Step 3: Commit**

```bash
git add backend/quiz_suite/test_anticheat.py
git commit -m "test(quiz-suite): anti-cheat tier — no key leak, server-graded, set pinned, ownership"
```

---

### Task 5: Failure-surfacing tier (API half)

Deliverable: a unit with no quiz content 404s honestly and never 500s.

**Files:**
- Create: `backend/quiz_suite/test_failure_surface.py`

**Interfaces:**
- Consumes: `test_journey.start_session`, `constants.UNIT_NOQUIZ`.
- Produces: nothing consumed later.

- [ ] **Step 1: Write the tests**

Create `backend/quiz_suite/test_failure_surface.py`:

```python
"""
When grading genuinely cannot happen, the API must say so honestly.

UNIT_NOQUIZ is seeded with a lesson and no quiz files at all, so this exercises
the real FileNotFoundError path rather than a mocked one.
"""

from __future__ import annotations

import pytest

from quiz_suite import constants as C
from quiz_suite.test_journey import start_session

pytestmark = pytest.mark.quiz_live


@pytest.mark.asyncio
async def test_missing_quiz_content_404s(api, auth_a):
    r = await api.get(f"/content/{C.UNIT_NOQUIZ}/quiz", headers=auth_a)
    assert r.status_code == 404, r.text


@pytest.mark.asyncio
async def test_answering_an_ungraded_unit_404s_not_500s(api, auth_a):
    session = await start_session(api, auth_a, unit_id=C.UNIT_NOQUIZ)
    r = await api.post(
        f"/progress/session/{session['session_id']}/answer",
        json={"question_id": "q1", "student_answer": 0, "ms_taken": 10},
        headers=auth_a,
    )
    assert r.status_code == 404, f"expected an honest 404, got {r.status_code}: {r.text}"


@pytest.mark.asyncio
async def test_failure_message_is_student_safe(api, auth_a):
    """Content Rule #5: no stack traces, status codes, or internal ids in the text."""
    session = await start_session(api, auth_a, unit_id=C.UNIT_NOQUIZ)
    r = await api.post(
        f"/progress/session/{session['session_id']}/answer",
        json={"question_id": "q1", "student_answer": 0, "ms_taken": 10},
        headers=auth_a,
    )
    detail = r.json().get("detail")
    message = detail.get("detail") if isinstance(detail, dict) else str(detail)
    lowered = message.lower()
    for leak in ("traceback", "filenotfounderror", "/data/content", "exception"):
        assert leak not in lowered, f"internal detail leaked to the student: {message}"
```

- [ ] **Step 2: Run**

Run:
```bash
docker compose exec -T api python -m pytest quiz_suite/test_failure_surface.py -m quiz_live -q
```
Expected: 3 PASS.

- [ ] **Step 3: Commit**

```bash
git add backend/quiz_suite/test_failure_surface.py
git commit -m "test(quiz-suite): failure tier — missing quiz content 404s honestly"
```

---

### Task 6: Content-integrity sweep

Deliverable: real on-disk content is checked for quiz data that would grade students wrongly.

**Files:**
- Create: `backend/quiz_suite/test_content_integrity.py`

**Interfaces:**
- Consumes: `constants.CONTENT_ROOT`.
- Produces: nothing consumed later.

- [ ] **Step 1: Write the sweep**

Create `backend/quiz_suite/test_content_integrity.py`:

```python
"""
Sweep REAL on-disk content — not the fixture — for quiz data that would grade
students incorrectly.

The sharp check is correct_option resolution: get_quiz_answer_key SKIPS any
question whose correct_option names an option that doesn't exist, so those
questions silently grade every student wrong. Nothing else in the codebase
notices.
"""

from __future__ import annotations

import glob
import json
import os

import pytest

from quiz_suite import constants as C

pytestmark = pytest.mark.quiz_live


def _real_quiz_files() -> list[str]:
    """Every quiz set on disk except the suite's own fixture."""
    pattern = os.path.join(C.CONTENT_ROOT, "*", "*", "quiz_set_*.json")
    return [p for p in glob.glob(pattern) if f"/{C.CURRICULUM_ID}/" not in p]


def test_real_content_is_present_or_loudly_skipped():
    files = _real_quiz_files()
    if not files:
        pytest.skip(
            "NO REAL QUIZ CONTENT ON THIS BOX (0 quiz_set_*.json outside the fixture) — "
            "the integrity sweep checked nothing. This is a skip, not a pass."
        )
    assert files


def test_every_quiz_set_parses_and_grades():
    files = _real_quiz_files()
    if not files:
        pytest.skip("no real quiz content on this box")

    broken: list[str] = []
    for path in files:
        rel = os.path.relpath(path, C.CONTENT_ROOT)
        try:
            with open(path) as fh:
                data = json.load(fh)
        except (json.JSONDecodeError, OSError) as exc:
            broken.append(f"{rel}: unreadable ({exc})")
            continue

        questions = data.get("questions")
        if not questions:
            broken.append(f"{rel}: no questions")
            continue

        for question in questions:
            qid = question.get("question_id") or "<missing question_id>"
            options = question.get("options") or []
            correct = question.get("correct_option")
            if not options:
                broken.append(f"{rel} {qid}: no options")
                continue
            if correct is None:
                broken.append(f"{rel} {qid}: no correct_option")
                continue
            if not any(o.get("option_id") == correct for o in options):
                broken.append(
                    f"{rel} {qid}: correct_option {correct!r} is not among "
                    f"{[o.get('option_id') for o in options]} — every student is graded wrong here"
                )

    assert not broken, "content that would misgrade students:\n" + "\n".join(broken)
```

- [ ] **Step 2: Run**

Run:
```bash
docker compose exec -T api python -m pytest quiz_suite/test_content_integrity.py -m quiz_live -q -rs
```
Expected: PASS, or a listed set of genuinely broken units. `-rs` prints the skip reason so an empty box is visible rather than silent. **If it reports broken content, that is a real finding — file an issue, do not weaken the check.**

- [ ] **Step 3: Prove the check bites — on a throwaway copy, never on real content**

Real generated content is expensive and has no reliable restore path, so the
proof runs against a disposable curriculum directory created and deleted here.

```bash
docker compose exec -T api python -c "
import json, os
d='/data/content/curricula/quizsuite-corrupt-probe/QS-PROBE-001'
os.makedirs(d, exist_ok=True)
json.dump({'unit_id':'QS-PROBE-001','set_number':1,'questions':[{
  'question_id':'q1','question_text':'probe','question_type':'multiple_choice',
  'options':[{'option_id':'A','text':'a'},{'option_id':'B','text':'b'}],
  'correct_option':'ZZZ','explanation':'','difficulty':'easy'}]},
  open(os.path.join(d,'quiz_set_1_en.json'),'w'))
print('probe written')"
docker compose exec -T api python -m pytest quiz_suite/test_content_integrity.py -m quiz_live -q
```
Expected: **FAIL**, naming `quizsuite-corrupt-probe/QS-PROBE-001 q1` and reporting
that `correct_option 'ZZZ'` is not among its options.

Then remove the probe and confirm the sweep is green again:
```bash
docker compose exec -T api rm -rf /data/content/curricula/quizsuite-corrupt-probe
docker compose exec -T api python -m pytest quiz_suite/test_content_integrity.py -m quiz_live -q
```
Expected: PASS.

**Do not modify any file under a real curriculum directory.** If the probe
directory is somehow not swept (because the sweep's glob excludes it), fix the
glob — do not reach for real content instead.

- [ ] **Step 4: Commit**

```bash
git add backend/quiz_suite/test_content_integrity.py
git commit -m "test(quiz-suite): integrity sweep — unresolvable correct_option misgrades silently"
```

---

### Task 7: Playwright project and browser journey spec

Deliverable: a real browser, no route mocks, proves Submit reveals the verdict and advances.

**Files:**
- Create: `web/tests/e2e/quiz-suite/quiz-journey.spec.ts`, `web/tests/e2e/quiz-suite/fixture.ts`
- Modify: `web/playwright.config.ts`

**Interfaces:**
- Consumes: `.fixture.json` copied to `web/tests/e2e/quiz-suite/.fixture.json` by the orchestrator (Task 9).
- Produces: `fixture.ts` exports `loadFixture(): QuizFixture` and `loginAsStudentA(page)`.

- [ ] **Step 1: Add the env-gated project**

In `web/playwright.config.ts`, inside the `projects` array, append:

```ts
    // ── Quiz suite (live stack, NO route mocks) ───────────────────────────
    // Env-gated so `npx playwright test` never runs it: it needs a seeded
    // fixture and a live backend. scripts/quiz_suite.sh sets QUIZ_SUITE=1.
    ...(process.env.QUIZ_SUITE
      ? [
          {
            name: "quiz-suite",
            testMatch: "**/e2e/quiz-suite/*.spec.ts",
            use: { ...devices["Desktop Chrome"] },
          },
        ]
      : []),
```

- [ ] **Step 2: Create the browser fixture helper**

Create `web/tests/e2e/quiz-suite/fixture.ts`:

```ts
/**
 * Shared helpers for the live quiz suite.
 *
 * Unlike every other spec in tests/e2e, these register NO route mocks — the
 * whole point is to exercise the real backend.
 */
import fs from "node:fs";
import path from "node:path";
import { expect, type Page } from "@playwright/test";

export interface QuizFixture {
  student_a_email: string;
  student_b_email: string;
  password: string;
  curriculum_id: string;
  unit_quiz: string;
  unit_noquiz: string;
  answer_key: Record<string, Record<string, number>>;
}

export function loadFixture(): QuizFixture {
  const file = path.join(__dirname, ".fixture.json");
  if (!fs.existsSync(file)) {
    throw new Error(`${file} missing — run scripts/quiz_suite.sh, which seeds first.`);
  }
  return JSON.parse(fs.readFileSync(file, "utf8")) as QuizFixture;
}

export async function loginAsStudentA(page: Page): Promise<void> {
  const fixture = loadFixture();
  await page.goto("/login");
  await page.getByLabel(/email/i).fill(fixture.student_a_email);
  await page.getByLabel(/password/i).fill(fixture.password);
  await page.getByRole("button", { name: /sign in|log in/i }).click();
  await expect(page).not.toHaveURL(/\/login/, { timeout: 15000 });
}
```

- [ ] **Step 3: Write the journey spec**

Create `web/tests/e2e/quiz-suite/quiz-journey.spec.ts`:

```ts
/**
 * The reported symptom of #524, asserted in a real browser:
 * "In Quiz - Submit is not taking me to the next question."
 */
import { test, expect } from "@playwright/test";
import { loadFixture, loginAsStudentA } from "./fixture";

test.describe("quiz journey (live stack)", () => {
  test("submit reveals the verdict and advances to the next question", async ({ page }) => {
    const fixture = loadFixture();
    await loginAsStudentA(page);
    await page.goto(`/quiz/${fixture.unit_quiz}`);

    await expect(page.getByText(/question 1 of/i)).toBeVisible({ timeout: 15000 });

    // Pick any option and submit.
    await page.getByRole("button", { name: /^Option /i }).first().click();
    await page.getByRole("button", { name: /submit answer/i }).click();

    // The verdict comes back from the real server, so the action button must
    // become "Next question". Before the fix this stayed on "Submit answer".
    await expect(page.getByRole("button", { name: /next question/i })).toBeVisible({
      timeout: 15000,
    });

    await page.getByRole("button", { name: /next question/i }).click();
    await expect(page.getByText(/question 2 of/i)).toBeVisible();
  });

  test("completing the quiz reaches a result screen with a real score", async ({ page }) => {
    const fixture = loadFixture();
    await loginAsStudentA(page);
    await page.goto(`/quiz/${fixture.unit_quiz}`);
    await expect(page.getByText(/question 1 of/i)).toBeVisible({ timeout: 15000 });

    // Walk all three questions.
    for (let i = 0; i < 3; i++) {
      await page.getByRole("button", { name: /^Option /i }).first().click();
      await page.getByRole("button", { name: /submit answer/i }).click();
      const next = page.getByRole("button", { name: /next question|see results/i });
      await expect(next).toBeVisible({ timeout: 15000 });
      await next.click();
    }

    await expect(page.getByText(/\d+\s*\/\s*3|attempt/i)).toBeVisible({ timeout: 15000 });
  });
});
```

- [ ] **Step 4: Confirm the default Playwright run ignores it**

Run from `web/`:
```bash
npx playwright test --list | grep -c "quiz-suite" || echo "0 — correctly excluded"
```
Expected: `0 — correctly excluded` (QUIZ_SUITE is unset).

- [ ] **Step 5: Run the project explicitly**

Seed first, copy the fixture, then run from `web/`:
```bash
docker compose exec -T api python -m quiz_suite.seed seed
docker compose cp api:/app/quiz_suite/.fixture.json web/tests/e2e/quiz-suite/.fixture.json
cd web && QUIZ_SUITE=1 npx playwright test --project=quiz-suite quiz-journey
```
Expected: 2 PASS. If the login step cannot find the fields, open `web/app/login/page.tsx` and match the real labels/roles — adjust `fixture.ts`, not the assertions.

- [ ] **Step 6: Commit**

```bash
git add web/playwright.config.ts web/tests/e2e/quiz-suite/
git commit -m "test(quiz-suite): browser journey spec on the live stack, no route mocks"
```

---

### Task 8: Browser failure spec

Deliverable: a grading failure shows the student a message; the button is not dead.

**Files:**
- Create: `web/tests/e2e/quiz-suite/quiz-failure.spec.ts`

**Interfaces:**
- Consumes: `fixture.ts` from Task 7.
- Produces: nothing consumed later.

- [ ] **Step 1: Write the spec**

Create `web/tests/e2e/quiz-suite/quiz-failure.spec.ts`:

```ts
/**
 * The second half of #524: when grading legitimately fails, the player must
 * SAY something. A silently dead button is what let the bug reach a QA pass.
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
```

- [ ] **Step 2: Run**

From `web/`:
```bash
QUIZ_SUITE=1 npx playwright test --project=quiz-suite quiz-failure
```
Expected: PASS. If the copy differs, read `web/lib/content-error.ts` for the real message and match it — do not loosen the regex to `/./`.

- [ ] **Step 3: Commit**

```bash
git add web/tests/e2e/quiz-suite/quiz-failure.spec.ts
git commit -m "test(quiz-suite): browser failure spec — no dead button, no leaked internals"
```

---

### Task 9: Orchestrator and `/quiz-suite` command

Deliverable: one command runs everything, distinguishes a broken stack from a broken build, and always tears down.

**Files:**
- Create: `scripts/quiz_suite.sh`, `.claude/commands/quiz-suite.md`

**Interfaces:**
- Consumes: everything above.
- Produces: exit codes `0` pass, `1` test failure, `2` environment problem.

- [ ] **Step 1: Write the orchestrator**

Create `scripts/quiz_suite.sh`:

```bash
#!/usr/bin/env bash
# =============================================================================
# scripts/quiz_suite.sh — the quiz testing suite (see
# docs/superpowers/specs/2026-08-01-quiz-testing-suite-design.md)
#
#   ./scripts/quiz_suite.sh              # everything
#   ./scripts/quiz_suite.sh --api-only
#   ./scripts/quiz_suite.sh --browser-only
#   ./scripts/quiz_suite.sh --keep       # leave the fixture in place
#
# Exit codes: 0 pass · 1 test failure · 2 environment problem.
# =============================================================================
set -uo pipefail

API_ONLY=0; BROWSER_ONLY=0; KEEP=0; VERBOSE=0
for arg in "$@"; do
  case "$arg" in
    --api-only) API_ONLY=1 ;;
    --browser-only) BROWSER_ONLY=1 ;;
    --keep) KEEP=1 ;;
    -v|--verbose) VERBOSE=1 ;;
    *) echo "unknown flag: $arg" >&2; exit 2 ;;
  esac
done

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
FIXTURE_WEB="web/tests/e2e/quiz-suite/.fixture.json"
# NO -e TEST_DB_URL= here. backend/tests/conftest.py downgrades to base at
# session end; blanking TEST_DB_URL points that at the DEV database and drops
# every table. The suite lives outside backend/tests/ so that conftest never
# applies, and seed.py reads DATABASE_URL, which is already the dev database.
DC_EXEC=(docker compose exec -T api)

# ── Preflight ────────────────────────────────────────────────────────────────
# A suite that can't tell "your code is broken" from "your stack isn't running"
# costs more than it saves.
echo "→ preflight"
if ! docker compose ps --status running --services 2>/dev/null | grep -qx api; then
  echo "✗ the 'api' container is not running. Start the stack first:" >&2
  echo "    ./dev_start.sh" >&2
  exit 2
fi
if ! "${DC_EXEC[@]}" python -c "
import sys, urllib.request
try:
    urllib.request.urlopen('http://localhost:8000/healthz', timeout=5)
except Exception as exc:
    print(exc, file=sys.stderr); sys.exit(1)
" >/dev/null 2>&1; then
  echo "✗ the api container is up but /healthz does not answer." >&2
  echo "    docker compose logs api --since 5m" >&2
  exit 2
fi
if [ "$API_ONLY" -eq 0 ]; then
  if ! docker compose ps --status running --services 2>/dev/null | grep -qx web; then
    echo "✗ the 'web' container is not running (needed for the browser tier)." >&2
    echo "    ./dev_start.sh   — or re-run with --api-only" >&2
    exit 2
  fi
fi
echo "  ok"

# ── Teardown always runs ─────────────────────────────────────────────────────
cleanup() {
  if [ "$KEEP" -eq 1 ]; then
    echo "→ --keep: leaving the fixture in place"
    return
  fi
  echo "→ teardown"
  "${DC_EXEC[@]}" python -m quiz_suite.seed teardown >/dev/null 2>&1 \
    || echo "  ⚠ teardown reported a problem; re-run with --keep and inspect"
  rm -f "$FIXTURE_WEB"
}
trap cleanup EXIT INT TERM

# ── Seed ─────────────────────────────────────────────────────────────────────
echo "→ seed"
if ! "${DC_EXEC[@]}" python -m quiz_suite.seed seed; then
  echo "✗ seeding failed" >&2
  exit 2
fi
mkdir -p "$(dirname "$FIXTURE_WEB")"
docker compose cp api:/app/quiz_suite/.fixture.json "$FIXTURE_WEB" >/dev/null

API_RESULT="skipped"; BROWSER_RESULT="skipped"; FAILED=0
PYTEST_FLAGS="-q -rs"
[ "$VERBOSE" -eq 1 ] && PYTEST_FLAGS="-v -rs"

# ── API tier ─────────────────────────────────────────────────────────────────
if [ "$BROWSER_ONLY" -eq 0 ]; then
  echo "→ API tier"
  start=$SECONDS
  if "${DC_EXEC[@]}" python -m pytest quiz_suite -m quiz_live $PYTEST_FLAGS; then
    API_RESULT="pass ($((SECONDS - start))s)"
  else
    API_RESULT="FAIL ($((SECONDS - start))s)"; FAILED=1
  fi
fi

# ── Browser tier ─────────────────────────────────────────────────────────────
if [ "$API_ONLY" -eq 0 ]; then
  echo "→ browser tier"
  start=$SECONDS
  if (cd web && QUIZ_SUITE=1 npx playwright test --project=quiz-suite); then
    BROWSER_RESULT="pass ($((SECONDS - start))s)"
  else
    BROWSER_RESULT="FAIL ($((SECONDS - start))s)"; FAILED=1
  fi
fi

# ── Summary ──────────────────────────────────────────────────────────────────
echo
echo "──────────────────────────────────────────────"
printf "  API tier      %s\n" "$API_RESULT"
printf "  Browser tier  %s\n" "$BROWSER_RESULT"
echo "──────────────────────────────────────────────"
if [ "$FAILED" -eq 1 ]; then
  echo "  ✗ quiz suite FAILED"
  echo "    correlation ids in the output map to: docker compose logs api --since 10m"
  exit 1
fi
echo "  ✓ quiz suite passed"
exit 0
```

- [ ] **Step 2: Make it executable and run it end to end**

```bash
chmod +x scripts/quiz_suite.sh
./scripts/quiz_suite.sh
```
Expected: preflight ok, seed, both tiers pass, teardown, `✓ quiz suite passed`, exit 0. Time it — if it exceeds 90s, note where.

- [ ] **Step 3: Verify the environment exit code**

```bash
docker compose stop web
./scripts/quiz_suite.sh; echo "exit=$?"
docker compose start web
```
Expected: `exit=2` with the `./dev_start.sh` hint — **not** a test failure.

- [ ] **Step 4: Verify teardown ran despite the failure**

```bash
docker compose exec -T api python -c "
import asyncio, asyncpg, os
async def main():
    c = await asyncpg.connect(os.environ['DATABASE_URL'])
    await c.execute(\"SET app.current_school_id = 'bypass'\")
    n = await c.fetchval('SELECT count(*) FROM students WHERE email LIKE \$1', 'quizsuite-%')
    print('leftover fixture students:', n)
    await c.close()
asyncio.run(main())"
```
Expected: `0`.

- [ ] **Step 5: Write the slash command**

Create `.claude/commands/quiz-suite.md`:

```markdown
---
description: Run the quiz testing suite against the live local stack. Explicit, ~90s.
---

Run the quiz suite and report the result.

## Step 1 — Run it

```bash
./scripts/quiz_suite.sh
```

## Step 2 — Interpret the exit code

| Exit | Meaning | What to do |
|---|---|---|
| 0 | Everything passed | Report pass, with tier timings. |
| 1 | A genuine test failure | Report which tier and which test. Pull the `correlation_id` from the output and fetch the matching server log: `docker compose logs api --since 10m \| grep <id>`. Do NOT weaken an assertion to make it pass. |
| 2 | Environment problem | The stack is not running or not healthy. Report that the suite did not run — this is NOT a passing result. Suggest `./dev_start.sh`. |

## Step 3 — On failure

Report the failing tier, the failing test names, and the server-side correlation id.
State plainly whether the quiz path is broken or the suite could not run — never
conflate the two.

Run this whenever `backend/src/progress/`, `backend/src/content/`,
`web/components/content/QuizPlayer.tsx`, or the quiz pages change.
```

- [ ] **Step 6: Commit**

```bash
git add scripts/quiz_suite.sh .claude/commands/quiz-suite.md
git commit -m "test(quiz-suite): orchestrator with preflight, result table, and /quiz-suite command"
```

---

### Task 10: Prove the suite earns its keep

Deliverable: documented evidence that reverting the #524 fix turns the suite red, and that nothing else regressed.

**Files:**
- Modify: `docs/superpowers/specs/2026-08-01-quiz-testing-suite-design.md` (append a "Verified" note)

**Interfaces:**
- Consumes: everything.
- Produces: nothing.

- [ ] **Step 1: Re-break the bug**

In `backend/src/progress/router.py::start_session`, replace the `resolve_curriculum_id(...)` call with:

```python
    curriculum_id = body.curriculum_id or "default"
```

Then: `docker compose restart api`

- [ ] **Step 2: Confirm the suite goes red**

```bash
./scripts/quiz_suite.sh; echo "exit=$?"
```
Expected: `exit=1`. The API tier fails `test_session_uses_the_resolved_curriculum_not_the_body` and `test_full_run_scores_what_the_student_earned`; the browser tier fails the "submit advances" spec. **Record the exact failing test names.**

- [ ] **Step 3: Restore and confirm green**

```bash
git checkout backend/src/progress/router.py
docker compose restart api
./scripts/quiz_suite.sh; echo "exit=$?"
```
Expected: `exit=0`.

- [ ] **Step 4: Confirm no collateral damage to the normal gates**

```bash
docker compose exec -T api python -m pytest -q 2>&1 | tail -3
cd web && npm run format:check && npm run lint && npx vitest run 2>&1 | tail -4
npx playwright test --list | grep -c "quiz-suite" || echo "0 — correctly excluded"
```
Expected: backend totals unchanged (1178 passed, 2 skipped); format/lint clean; vitest 839 passed; `0 — correctly excluded`.

- [ ] **Step 5: Record the evidence in the spec**

Append to `docs/superpowers/specs/2026-08-01-quiz-testing-suite-design.md`:

```markdown
## 10. Verification record

Acceptance criterion 2 exercised on <DATE>: reverting the #524 fix
(`curriculum_id = body.curriculum_id or "default"` in `start_session`) turned the
suite red — API tier `test_session_uses_the_resolved_curriculum_not_the_body`
and `test_full_run_scores_what_the_student_earned`, browser tier
"submit reveals the verdict and advances". Restoring the fix returned it green.

Measured runtime: <SECONDS>s (budget: 90s).
```

Replace `<DATE>` and `<SECONDS>` with the real values observed.

- [ ] **Step 6: Commit and open the PR**

```bash
git add docs/superpowers/specs/2026-08-01-quiz-testing-suite-design.md
git commit -m "docs(spec): record quiz-suite verification against the #524 revert"
git push -u origin feat/quiz-testing-suite-spec
gh pr create --base main --title "test(quiz-suite): live-stack quiz testing suite" --body "..."
```

The PR body must state: what the suite covers, the measured runtime, the evidence
from Step 2 that it catches #524, and that it is deliberately excluded from CI
(marker + env-gated Playwright project).

---

## Self-Review

**Spec coverage.** §2 areas 1–4 → Tasks 3, 4, 5, 6. §3 architecture → Tasks 1, 7, 9. §4 fixture → Task 2. §5.1–5.5 assertions → Tasks 3, 4, 5, 6, 7, 8. §6 diagnostics → Task 9. §7 CI exclusion → Task 1 Step 5 and Task 7 Step 4. §8 acceptance → Task 10. No spec section is unimplemented.

**Placeholder scan.** Every code step contains runnable content. The one `"..."` is the PR body in Task 10 Step 6, whose required contents are spelled out in the following sentence.

**Type consistency.** `constants` names are defined once in Task 1 and used verbatim thereafter. `answer_key` is `{set_number_as_string: {question_id: correct_index}}` in `seed.expected_answer_key()`, in `.fixture.json`, in the Python tests, and in `QuizFixture` in `fixture.ts`. `start_session`/`serve_quiz`/`answer_all` are defined in Task 3 and imported by Tasks 4 and 5 under those exact names. Exit codes 0/1/2 are consistent across Task 9, the slash command, and the spec.

**Known soft spots**, flagged rather than hidden:

- Task 3 Step 2 and Task 7 Step 5 tell the implementer to match the *real* response shape and the *real* login form rather than assume mine. Those are the two places where reading the running code beats trusting this plan.
- The 90-second budget is an estimate. Task 9 Step 2 measures it; if the browser tier blows it, cutting to one browser spec is the intended remedy.
