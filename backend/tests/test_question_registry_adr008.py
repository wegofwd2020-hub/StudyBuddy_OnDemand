"""The question registry — ADR-008 Phase 3a.

Phases 1 and 2 gave a question an identity and let a person point at one. Neither
gave the platform anywhere to KEEP a question: bodies live in the content store
addressed by set file, so the only way to enumerate a unit's questions is to open
`quiz_set_1/2/3`. That is *why* a quiz is a fixed set — there is no list to draw
from. Migration 0069 is that list.

These tests cover the two properties a pool actually depends on:

  * **deduplication by identity.** Two sets holding the same question must
    collapse to ONE drawable row. This is not hypothetical tidiness: Authoring
    Studio output repeats 82% of its stems, and one measured unit had 24
    questions of which 1 was distinct. A registry that concatenated sets would
    build a pool that draws the same question eight times.
  * **idempotence that preserves human decisions.** Re-running after a content
    regeneration must refresh what the generator owns (difficulty) and must NOT
    resurrect a question a person retired.
"""

from __future__ import annotations

import uuid

import asyncpg
import pytest

from src.core.question_identity import stable_question_id

CUR = "registry-test-curriculum"
UNIT = "REG-MATH-001"


async def _rows(db_conn, unit_id: str = UNIT):
    return await db_conn.fetch(
        "SELECT * FROM question_registry WHERE curriculum_id = $1 AND unit_id = $2"
        " ORDER BY stable_question_id",
        CUR,
        unit_id,
    )


async def _register(
    db_conn, stem: str, *, difficulty: str | None, source_set: int, unit_id: str = UNIT
):
    """The upsert the backfill performs, kept identical so the tests exercise it."""
    qid = stable_question_id(CUR, unit_id, "en", stem)
    await db_conn.execute(
        """
        INSERT INTO question_registry
            (stable_question_id, curriculum_id, unit_id, lang, difficulty, source_set)
        VALUES ($1, $2, $3, 'en', $4, $5)
        ON CONFLICT (stable_question_id) DO UPDATE
            SET difficulty = EXCLUDED.difficulty,
                source_set = COALESCE(question_registry.source_set, EXCLUDED.source_set)
        """,
        qid,
        CUR,
        unit_id,
        difficulty,
        source_set,
    )
    return qid


# ── Deduplication ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_the_same_question_in_two_sets_becomes_one_row(db_conn):
    """The property the whole pool rests on."""
    unit = f"{UNIT}-dedupe"
    stem = "Which of the following is a prime number?"
    a = await _register(db_conn, stem, difficulty="easy", source_set=1, unit_id=unit)
    b = await _register(db_conn, stem, difficulty="easy", source_set=2, unit_id=unit)

    assert a == b, "identity must not depend on which set the question came from"
    rows = await _rows(db_conn, unit)
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_differently_worded_questions_stay_separate(db_conn):
    """The negative direction. A registry that collapsed everything would pass the
    test above and produce a pool of one question per unit."""
    unit = f"{UNIT}-distinct"
    await _register(db_conn, "What is 2 + 2?", difficulty="easy", source_set=1, unit_id=unit)
    await _register(db_conn, "What is 3 + 3?", difficulty="easy", source_set=1, unit_id=unit)

    assert len(await _rows(db_conn, unit)) == 2


@pytest.mark.asyncio
async def test_the_same_stem_in_a_different_unit_is_a_different_question(db_conn):
    """Identity includes the unit, so a stem reused across units — common for
    definitional questions — does not merge two units' pools into one."""
    stem = "Define velocity."
    await _register(db_conn, stem, difficulty="medium", source_set=1, unit_id=f"{UNIT}-u1")
    await _register(db_conn, stem, difficulty="medium", source_set=1, unit_id=f"{UNIT}-u2")

    assert len(await _rows(db_conn, f"{UNIT}-u1")) == 1
    assert len(await _rows(db_conn, f"{UNIT}-u2")) == 1


# ── Idempotence, and what a re-import may not undo ────────────────────────────


@pytest.mark.asyncio
async def test_reimport_refreshes_difficulty(db_conn):
    """The generator owns difficulty, so a regeneration that corrects it must win."""
    unit = f"{UNIT}-refresh"
    stem = "Explain conservation of momentum."
    await _register(db_conn, stem, difficulty="easy", source_set=1, unit_id=unit)
    await _register(db_conn, stem, difficulty="hard", source_set=1, unit_id=unit)

    rows = await _rows(db_conn, unit)
    assert len(rows) == 1
    assert rows[0]["difficulty"] == "hard"


@pytest.mark.asyncio
async def test_reimport_does_not_resurrect_a_retired_question(db_conn):
    """The reason the upsert names its columns instead of replacing the row.

    Retirement is a human decision — a question found to be wrong or ambiguous.
    A content re-import must not silently undo it and put the question back in
    front of students.
    """
    unit = f"{UNIT}-retired"
    stem = "An ambiguous question about tides."
    qid = await _register(db_conn, stem, difficulty="medium", source_set=1, unit_id=unit)
    await db_conn.execute(
        "UPDATE question_registry SET status='retired' WHERE stable_question_id=$1", qid
    )

    await _register(db_conn, stem, difficulty="medium", source_set=1, unit_id=unit)

    row = await db_conn.fetchrow(
        "SELECT status FROM question_registry WHERE stable_question_id=$1", qid
    )
    assert row["status"] == "retired"


@pytest.mark.asyncio
async def test_provenance_records_where_it_was_first_seen(db_conn):
    """`source_set` is provenance, so it must not drift to whichever set the
    importer happened to read last."""
    unit = f"{UNIT}-prov"
    stem = "First seen in set 1."
    await _register(db_conn, stem, difficulty="easy", source_set=1, unit_id=unit)
    await _register(db_conn, stem, difficulty="easy", source_set=3, unit_id=unit)

    rows = await _rows(db_conn, unit)
    assert rows[0]["source_set"] == 1


# ── Constraints ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_status_is_constrained(db_conn):
    """A typo'd status would silently remove a question from every draw, because
    the draw filters on status='active'."""
    unit = f"{UNIT}-status"
    qid = await _register(db_conn, "Status check.", difficulty="easy", source_set=1, unit_id=unit)
    # The SPECIFIC violation, not a blind Exception. `pytest.raises(Exception)`
    # would pass just as happily on a typo in the SQL or a missing table — the
    # test would be green while proving nothing about the constraint.
    with pytest.raises(asyncpg.exceptions.CheckViolationError) as exc:
        await db_conn.execute(
            "UPDATE question_registry SET status='disabled' WHERE stable_question_id=$1", qid
        )
    assert "question_registry_status_check" in str(exc.value)


@pytest.mark.asyncio
async def test_difficulty_is_constrained_but_may_be_absent(db_conn):
    """NULL is allowed — a question whose body lacks difficulty must still be
    registrable rather than silently dropped from the pool — but a wrong value is
    not, because the stratified draw buckets on it."""
    unit = f"{UNIT}-diff"
    await _register(db_conn, "No difficulty given.", difficulty=None, source_set=1, unit_id=unit)
    rows = await _rows(db_conn, unit)
    assert rows[0]["difficulty"] is None

    with pytest.raises(asyncpg.exceptions.CheckViolationError) as exc:
        await db_conn.execute(
            """
            INSERT INTO question_registry
                (stable_question_id, curriculum_id, unit_id, lang, difficulty)
            VALUES ($1, $2, $3, 'en', 'trivial')
            """,
            uuid.uuid4().hex[:16],
            CUR,
            unit,
        )
    assert "question_registry_difficulty_check" in str(exc.value)
