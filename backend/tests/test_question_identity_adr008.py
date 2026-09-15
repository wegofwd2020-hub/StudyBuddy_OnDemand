"""Stable question identity — ADR-008 Phase 1.

`progress_answers.question_id` holds `q1…qN`, a position WITHIN a quiz set, so
`q1` of set 2 is a different question from `q1` of set 1 in the same unit.
Grouping by it groups questions that merely share an index — which is why the
per-answer data already being collected (including `ms_taken`) cannot be
aggregated, and why every other part of ADR-008 is blocked behind this one.

The identity is content-addressed rather than a minted UUID so that the ~12,500
questions already on disk can be backfilled in place instead of regenerated.

These tests pin the SCOPE of the hash, because scope is the whole design:
what counts as the same question, and what counts as a different one. Getting it
wrong is not a crash — it silently merges or splits the statistics that Decision 8
is built on, which is the kind of error that only shows up a year later in an
analysis nobody can reproduce.
"""

from __future__ import annotations

import uuid

import pytest

from src.core.question_identity import (
    QUESTION_ID_LENGTH,
    stable_question_id,
    stable_question_ids_for_set,
)

CUR = "default-2026-g10"
UNIT = "G10-MATH-001"
STEM = "Which of the following is a prime number?"


# ── Shape ─────────────────────────────────────────────────────────────────────


def test_the_id_is_deterministic():
    """Recomputing anywhere must give the same answer — nothing stores a mapping."""
    a = stable_question_id(CUR, UNIT, "en", STEM)
    b = stable_question_id(CUR, UNIT, "en", STEM)
    assert a == b
    assert len(a) == QUESTION_ID_LENGTH
    assert a.islower() and all(c in "0123456789abcdef" for c in a)


# ── What counts as the SAME question ──────────────────────────────────────────


def test_the_same_question_in_two_sets_is_one_question():
    """The property the whole ADR rests on.

    A question reached through set 1 and through set 3 of one unit is one item and
    must accumulate one body of evidence. The set number is deliberately NOT part
    of the identity — including it would reproduce the exact defect being fixed,
    just with longer ids.
    """
    # Demonstrated through the set-level mapping, at DIFFERENT positions -- calling
    # the function twice with identical arguments would only re-test determinism.
    set_1 = [
        {"question_id": "q1", "question_text": STEM},
        {"question_id": "q2", "question_text": "Filler?"},
    ]
    set_3 = [
        {"question_id": "q1", "question_text": "Something else?"},
        {"question_id": "q2", "question_text": "Another?"},
        {"question_id": "q5", "question_text": STEM},
    ]
    m1, _ = stable_question_ids_for_set(CUR, UNIT, "en", set_1)
    m3, _ = stable_question_ids_for_set(CUR, UNIT, "en", set_3)

    assert m1["q1"] == m3["q5"], "same stem at q1 and at q5 must be one identity"
    assert m1["q1"] != m3["q1"], "and different stems at the same POSITION must not be"

    import inspect

    assert "set_number" not in inspect.signature(stable_question_id).parameters, (
        "including the set number would reproduce the defect with longer ids"
    )


def test_reflowed_whitespace_is_the_same_question():
    """A content file re-wrapped by a formatter must not mint a new identity."""
    reflowed = "Which of the following\n  is a  prime number?"
    assert stable_question_id(CUR, UNIT, "en", reflowed) == stable_question_id(
        CUR, UNIT, "en", STEM
    )


def test_unicode_composition_is_the_same_question():
    """Composed vs decomposed accents are the same text to a reader."""
    composed = "Qu'est-ce qu'un nombre premieré"  # é as one code point
    decomposed = "Qu'est-ce qu'un nombre premieré"  # e + combining acute
    assert stable_question_id(CUR, UNIT, "fr", composed) == stable_question_id(
        CUR, UNIT, "fr", decomposed
    )


# ── What counts as a DIFFERENT question ───────────────────────────────────────


def test_the_same_stem_in_another_unit_is_another_question():
    """Different unit means a different cohort having studied different material."""
    assert stable_question_id(CUR, UNIT, "en", STEM) != stable_question_id(
        CUR, "G10-MATH-002", "en", STEM
    )


def test_each_language_is_its_own_question():
    """Deliberate: a translation can be measurably harder than its source."""
    assert stable_question_id(CUR, UNIT, "en", STEM) != stable_question_id(
        CUR, UNIT, "fr", STEM
    )


def test_a_reworded_question_is_a_new_question():
    """This is where the implementation departs from ADR-008 Decision 4.

    The ADR says the id "does not change when a question is revised". It should:
    a reworded item's old difficulty and discrimination do not describe the new
    wording, and carrying them across would corrupt the analysis Decision 8
    depends on. Continuity across a revision is the Phase 3 registry's job — it
    can record "v2 supersedes v1" explicitly, which an identifier cannot.
    """
    reworded = "Which of these numbers is prime?"
    assert stable_question_id(CUR, UNIT, "en", STEM) != stable_question_id(
        CUR, UNIT, "en", reworded
    )


def test_reordering_options_does_not_change_the_question():
    """Only the stem is hashed. Shuffling options, or fixing a mis-keyed answer,
    leaves the same item — its accumulated evidence should survive both."""
    # The function takes only the stem, so this is a statement about the SCOPE:
    # options are not an input, and cannot silently split an item's identity.
    import inspect

    params = inspect.signature(stable_question_id).parameters
    assert "options" not in params and "correct_option" not in params


# ── Set-level mapping ─────────────────────────────────────────────────────────


def test_mapping_covers_every_question_in_a_set():
    questions = [
        {"question_id": "q1", "question_text": "First question?"},
        {"question_id": "q2", "question_text": "Second question?"},
        {"question_id": "q3", "question_text": "Third question?"},
    ]
    mapping, collisions = stable_question_ids_for_set(CUR, UNIT, "en", questions)
    assert set(mapping) == {"q1", "q2", "q3"}
    assert len(set(mapping.values())) == 3, "distinct stems must get distinct ids"
    assert collisions == []


def test_a_repeated_stem_inside_one_set_is_reported_not_hidden():
    """Authoring Studio scratch projects repeat stems — 4,557 of 5,608 questions.

    Real content has none (platform: 5,760 questions, zero; school forks: 1,200,
    zero), but a silent collision would merge two questions' statistics into one.
    Reported rather than resolved: the fix belongs in the content.
    """
    questions = [
        {"question_id": "q1", "question_text": "What is speed?"},
        {"question_id": "q2", "question_text": "What is speed?"},
    ]
    mapping, collisions = stable_question_ids_for_set(CUR, UNIT, "en", questions)
    assert collisions == ["q2"]
    assert mapping["q1"] == mapping["q2"], "same stem genuinely is the same id"


def test_questions_without_a_stem_are_skipped_not_crashed():
    questions = [
        {"question_id": "q1", "question_text": "Real question?"},
        {"question_id": "q2"},  # malformed content
        {"question_text": "no positional id"},
    ]
    mapping, _ = stable_question_ids_for_set(CUR, UNIT, "en", questions)
    assert set(mapping) == {"q1"}


# ── The answer key carries it ─────────────────────────────────────────────────


def test_the_answer_key_carries_the_stable_id():
    """Grading resolves the key; the id has to ride along with it, or the write
    path has nothing to record and the client contract would have to change."""
    from src.content.service import _parse_quiz_answer_key

    body = {
        "questions": [
            {
                "question_id": "q1",
                "question_text": STEM,
                "correct_option": "B",
                "options": [
                    {"option_id": "A", "text": "4"},
                    {"option_id": "B", "text": "7"},
                ],
                "explanation": "7 has no divisors besides 1 and itself.",
            }
        ]
    }
    key = _parse_quiz_answer_key(body, CUR, UNIT, 1, "en")
    assert key["q1"]["index"] == 1, "grading must still work"
    assert key["q1"]["stable_question_id"] == stable_question_id(CUR, UNIT, "en", STEM)


def test_the_key_computes_the_id_rather_than_trusting_the_file():
    """Content generated before the backfill has no id field. Computing it from
    the stem means old content still resolves, so no code path silently records
    NULL because a file predates this work."""
    from src.content.service import _parse_quiz_answer_key

    body = {
        "questions": [
            {
                "question_id": "q1",
                "question_text": STEM,
                # deliberately no stable id stored on the question
                "correct_option": "A",
                "options": [{"option_id": "A", "text": "7"}],
            }
        ]
    }
    key = _parse_quiz_answer_key(body, CUR, UNIT, 1, "en")
    assert key["q1"]["stable_question_id"] == stable_question_id(CUR, UNIT, "en", STEM)


# ── It reaches the database ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_an_answer_persists_the_stable_id(client, db_conn):
    """End of the chain: the column exists and the write path fills it."""
    from src.progress.service import record_answer_sync

    pool = client._transport.app.state.pool
    sid = str(uuid.uuid4())
    expected = stable_question_id(CUR, UNIT, "en", STEM)

    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        student_id = str(uuid.uuid4())
        await conn.execute(
            """
            INSERT INTO students (student_id, external_auth_id, email, name, grade, locale)
            VALUES ($1, $2, $3, 'Identity Student', 10, 'en')
            """,
            uuid.UUID(student_id),
            f"auth0|qid-{student_id.replace('-', '')}",
            f"qid-{student_id[:8]}@example.com",
        )
        await conn.execute(
            """
            INSERT INTO progress_sessions
                (session_id, student_id, unit_id, curriculum_id, grade, subject,
                 attempt_number, completed)
            VALUES ($1, $2, $3, $4, 10, 'Mathematics', 1, FALSE)
            """,
            uuid.UUID(sid),
            uuid.UUID(student_id),
            UNIT,
            CUR,
        )
        await record_answer_sync(
            conn,
            session_id=sid,
            question_id="q1",
            student_answer=1,
            correct_answer=1,
            correct=True,
            ms_taken=4200,
            event_id=None,
            stable_question_id=expected,
        )
        row = await conn.fetchrow(
            "SELECT question_id, stable_question_id FROM progress_answers "
            "WHERE session_id = $1",
            uuid.UUID(sid),
        )

    assert row is not None
    assert row["question_id"] == "q1", "the positional id stays, as a display ordinal"
    assert row["stable_question_id"] == expected


@pytest.mark.asyncio
async def test_an_answer_without_an_id_still_writes(client, db_conn):
    """The column is nullable on purpose. A caller that has no id — an older
    client, or a replayed offline event — must still record the answer rather
    than lose a student's work to a column added for analytics."""
    from src.progress.service import record_answer_sync

    pool = client._transport.app.state.pool
    sid = str(uuid.uuid4())
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        student_id = str(uuid.uuid4())
        await conn.execute(
            """
            INSERT INTO students (student_id, external_auth_id, email, name, grade, locale)
            VALUES ($1, $2, $3, 'Nullable Student', 10, 'en')
            """,
            uuid.UUID(student_id),
            f"auth0|qidn-{student_id.replace('-', '')}",
            f"qidn-{student_id[:8]}@example.com",
        )
        await conn.execute(
            """
            INSERT INTO progress_sessions
                (session_id, student_id, unit_id, curriculum_id, grade, subject,
                 attempt_number, completed)
            VALUES ($1, $2, $3, $4, 10, 'Mathematics', 1, FALSE)
            """,
            uuid.UUID(sid),
            uuid.UUID(student_id),
            UNIT,
            CUR,
        )
        await record_answer_sync(
            conn,
            session_id=sid,
            question_id="q1",
            student_answer=0,
            correct_answer=0,
            correct=True,
            ms_taken=1000,
            event_id=None,
        )
        row = await conn.fetchrow(
            "SELECT stable_question_id FROM progress_answers WHERE session_id = $1",
            uuid.UUID(sid),
        )

    assert row is not None
    assert row["stable_question_id"] is None
