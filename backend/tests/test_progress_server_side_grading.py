"""
tests/test_progress_server_side_grading.py

Quiz grading is the server's job.

Before this, `POST /progress/session/{id}/answer` accepted `correct: bool` and
`POST /progress/session/{id}/end` accepted `score: int`, and the backend stored
whatever the browser sent. The quiz payload also shipped `correct_option` for
every question. Between them, a student could read the answers out of the network
tab and then post themselves a perfect score.

Now:
  - the client sends only which option it picked
  - the server resolves the correct option from the content store and grades it
  - the score at end-of-session is the server's running tally, not a request field
  - the served quiz carries no answer key at all
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.content.router import _strip_answer_key
from src.content.service import get_quiz_answer_key
from src.progress.service import (
    read_tally,
    resolve_session_quiz_set,
    tally_answer,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────

# Correct answer is "B" — and note B is NOT at alphabetical index 1 in the option
# list: the options are deliberately ordered C, B, A so that a grader keying off
# alphabetical position instead of the option's real position would get it wrong.
QUIZ_SET_2 = {
    "unit_id": "G10-ENG-001",
    "set_number": 2,
    "questions": [
        {
            "question_id": "q1",
            "question_text": "What holds the beam up?",
            "question_type": "multiple_choice",
            "options": [
                {"option_id": "C", "text": "Magic"},
                {"option_id": "B", "text": "The support reaction"},
                {"option_id": "A", "text": "Nothing"},
            ],
            "correct_option": "B",
            "explanation": "The support reaction balances the load.",
            "difficulty": "medium",
        },
        {
            "question_id": "q2",
            "question_text": "Second question?",
            "question_type": "multiple_choice",
            "options": [
                {"option_id": "A", "text": "Right"},
                {"option_id": "B", "text": "Wrong"},
            ],
            "correct_option": "A",
            "explanation": "A is right.",
            "difficulty": "easy",
        },
    ],
    "model": "claude-sonnet-4-6",
}


def _redis_store() -> MagicMock:
    """A MagicMock redis with a real dict behind it, so INCR/GET actually work."""
    data: dict[str, str] = {}

    async def _get(k):
        return data.get(k)

    async def _set(k, v, ex=None):
        data[k] = str(v)

    async def _incr(k):
        data[k] = str(int(data.get(k, 0)) + 1)
        return int(data[k])

    async def _setnx(k, v):
        if k not in data:
            data[k] = str(v)
            return True
        return False

    async def _expire(k, ttl):
        return True

    r = MagicMock()
    r.get, r.set, r.incr, r.setnx, r.expire = (
        AsyncMock(side_effect=_get),
        AsyncMock(side_effect=_set),
        AsyncMock(side_effect=_incr),
        AsyncMock(side_effect=_setnx),
        AsyncMock(side_effect=_expire),
    )
    r._data = data
    return r


def _storage(payload: dict) -> MagicMock:
    s = MagicMock()
    s.read_json = AsyncMock(return_value=payload)
    return s


# ── The answer key never leaves the server ────────────────────────────────────


def test_served_quiz_carries_no_answer_key():
    stripped = _strip_answer_key(QUIZ_SET_2)

    for q in stripped["questions"]:
        assert "correct_option" not in q
        assert "explanation" not in q

    # Everything the student legitimately needs survives.
    assert stripped["questions"][0]["question_text"] == "What holds the beam up?"
    assert len(stripped["questions"][0]["options"]) == 3
    assert stripped["set_number"] == 2


def test_strip_does_not_mutate_the_cached_source():
    """The dict handed to _strip_answer_key may be the L2-cached object."""
    original = json.loads(json.dumps(QUIZ_SET_2))
    _strip_answer_key(original)
    assert original["questions"][0]["correct_option"] == "B"


# ── Grading resolves the key from the content store ───────────────────────────


@pytest.mark.asyncio
async def test_answer_key_uses_option_position_not_alphabetical_order():
    """
    The correct option is "B", which sits at position 1 in an option list ordered
    C, B, A. A grader that mapped "B" → alphabetical index 1 would get the right
    answer here by luck; one that mapped "A" → 0 would mark q1's real answer wrong.
    Pin the behaviour: the index is the option's position in ITS OWN list.
    """
    key = await get_quiz_answer_key(
        "default-2026-g10", "G10-ENG-001", 2, "en", _redis_store(), _storage(QUIZ_SET_2)
    )

    assert key["q1"]["index"] == 1  # "B" is the 2nd option in the C, B, A list
    assert key["q2"]["index"] == 0  # "A" is the 1st option in the A, B list
    assert key["q1"]["explanation"] == "The support reaction balances the load."


@pytest.mark.asyncio
async def test_answer_key_skips_question_whose_correct_option_is_not_an_option():
    """A content defect must not silently mark every answer wrong."""
    broken = json.loads(json.dumps(QUIZ_SET_2))
    broken["questions"][0]["correct_option"] = "Z"  # not present in options

    key = await get_quiz_answer_key(
        "default-2026-g10", "G10-ENG-001", 2, "en", _redis_store(), _storage(broken)
    )

    assert "q1" not in key  # unresolvable → excluded, logged
    assert "q2" in key


# ── The score is the server's tally, not the client's claim ───────────────────


@pytest.mark.asyncio
async def test_tally_counts_only_server_graded_correct_answers():
    redis = _redis_store()
    session = "11111111-1111-1111-1111-111111111111"

    await tally_answer(redis, session_id=session, correct=True)
    await tally_answer(redis, session_id=session, correct=False)
    await tally_answer(redis, session_id=session, correct=True)

    assert await read_tally(redis, session) == 2


@pytest.mark.asyncio
async def test_all_wrong_run_tallies_zero_not_missing():
    """
    An all-wrong run must read back as 0, distinguishable from "no tally at all"
    (None) — otherwise end_session would fall back to the DB and could report a
    stale or partial number.
    """
    redis = _redis_store()
    session = "22222222-2222-2222-2222-222222222222"

    await tally_answer(redis, session_id=session, correct=False)
    await tally_answer(redis, session_id=session, correct=False)

    assert await read_tally(redis, session) == 0


@pytest.mark.asyncio
async def test_read_tally_is_none_when_session_never_graded():
    assert await read_tally(_redis_store(), "33333333-3333-3333-3333-333333333333") is None


# ── The graded set is pinned for the life of the session ──────────────────────


@pytest.mark.asyncio
async def test_quiz_set_is_pinned_and_survives_rotation_advancing():
    """
    `question_id` is q1..qN in EVERY set, with different correct answers per set.
    So the set must stay fixed for the session: if the per-unit rotation pointer
    advances mid-quiz (student opens the unit again in another tab), later answers
    must still be graded against the set the student is actually holding.
    """
    redis = _redis_store()
    session, student, unit = "s-1", "stu-1", "G10-ENG-001"

    await redis.set("quiz_set:stu-1:G10-ENG-001", "2")
    assert await resolve_session_quiz_set(redis, session, student, unit) == 2

    # Rotation moves on — the pinned session must not follow it.
    await redis.set("quiz_set:stu-1:G10-ENG-001", "3")
    assert await resolve_session_quiz_set(redis, session, student, unit) == 2


@pytest.mark.asyncio
async def test_quiz_set_defaults_to_1_when_rotation_pointer_expired():
    redis = _redis_store()
    assert await resolve_session_quiz_set(redis, "s-2", "stu-2", "G10-ENG-001") == 1
