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
from datetime import UTC, datetime

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
    # get_quiz() serves this file's contents straight into QuizResponse — unlike
    # lessons there is no server-side normalization step — so every field the
    # schema requires (backend/src/content/schemas.py::QuizResponse) must be
    # present here, not just unit_id/set_number/questions.
    return {
        "unit_id": C.UNIT_QUIZ,
        "set_number": set_number,
        "language": "en",
        "questions": questions,
        "total_questions": len(questions),
        "estimated_duration_minutes": 5,
        "passing_score": 2,
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "model": "quiz-suite-fixture",
        "content_version": 1,
    }


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
        "generated_at": datetime.now(tz=UTC).isoformat(),
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
    # content_subject_versions has no FK/cascade from curricula (curriculum_id
    # is a bare text column here) — must be deleted explicitly or teardown
    # leaves an orphan row and a re-seed's "published" check reads stale state.
    await conn.execute("DELETE FROM content_subject_versions WHERE curriculum_id = $1", C.CURRICULUM_ID)
    await conn.execute("DELETE FROM curricula WHERE curriculum_id = $1", C.CURRICULUM_ID)
    await conn.execute("DELETE FROM schools WHERE school_id = $1", C.SCHOOL_ID)


async def _seed_rows(conn: asyncpg.Connection, password_hash: str) -> None:
    await conn.execute(
        "INSERT INTO schools (school_id, name, contact_email, country, status) "
        "VALUES ($1, $2, $3, 'CA', 'active')",
        C.SCHOOL_ID, "Quiz Suite Fixture School", "quizsuite-school@quizsuite.example.com",
    )
    await conn.execute(
        "INSERT INTO curricula (curriculum_id, grade, year, name, is_default, school_id, "
        "owner_type, source_type, status) "
        "VALUES ($1, $2, $3, $4, FALSE, $5, 'school', 'default', 'active')",
        C.CURRICULUM_ID, C.GRADE, C.YEAR, "Quiz Suite Fixture Curriculum", C.SCHOOL_ID,
    )
    for unit_id, title in ((C.UNIT_QUIZ, "Quiz Suite Unit"), (C.UNIT_NOQUIZ, "Quiz Suite No-Quiz Unit")):
        # unit_name is NOT NULL — omitting it fails the insert (pitfall #30).
        # content_status CHECK only allows pending/built/failed (not
        # 'published' — that value doesn't exist on this column); our
        # fixture files are already on disk, so 'built' is correct.
        await conn.execute(
            "INSERT INTO curriculum_units (unit_id, curriculum_id, subject, title, unit_name, "
            "sort_order, sequence, content_status) VALUES ($1, $2, $3, $4, $4, 1, 1, 'built')",
            unit_id, C.CURRICULUM_ID, C.SUBJECT, title,
        )
    # check_content_published() gates every content-serving endpoint on a
    # content_subject_versions row with status='published' for this
    # (curriculum_id, subject) — curriculum_units alone is not enough.
    # Without this insert every /content/{unit}/* endpoint 404s with
    # content_not_available regardless of what's on disk.
    await conn.execute(
        "INSERT INTO content_subject_versions (curriculum_id, subject, status, published_at) "
        "VALUES ($1, $2, 'published', $3)",
        C.CURRICULUM_ID, C.SUBJECT, datetime.now(tz=UTC),
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

    # check_content_published() caches a negative result in Redis
    # (csv:{curriculum_id}:{subject}, TTL 300s). A prior failed/partial run
    # (or a previous teardown-less crash) can leave that "0" cached, which
    # would make a freshly-seeded, correctly-published unit keep 404ing for
    # up to 5 minutes. Flush before handing back the fixture.
    await _flush_redis()

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
