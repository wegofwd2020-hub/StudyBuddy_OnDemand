"""
#529 — quiz grading must resolve content the SAME way serving does.

Before this fix the grading path graded against `session.curriculum_id` verbatim.
For a school on a FORKED curriculum that id has no store content (it lives under
the OOB source) → every answer 404'd. And a teacher OVERRIDE was served but graded
against the store file → silent misgrade (pitfall #35: q1…qN are identical ids
across sets/bodies).

These pin the two collaborators the grading path now shares with serving:
`resolve_content_curriculum` (the fork→OOB swap) and `resolve_quiz_answer_key`
(override-first, then fork-swap + store). Pure unit tests — the DB/store/redis
collaborators are mocked, so the resolution ORDER is what's asserted.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

import src.content.service as svc

# A teacher-override quiz body: same shape as a store quiz set. "B" is correct →
# index 1 in this A,B list. Deliberately different from STORE_KEY's index 0 so a
# test can tell which source was used.
OVERRIDE_BODY = {
    "questions": [
        {
            "question_id": "q1",
            "options": [{"option_id": "A"}, {"option_id": "B"}],
            "correct_option": "B",
            "explanation": "override says B",
        }
    ]
}
STORE_KEY = {"q1": {"index": 0, "explanation": "store says A"}}


# ── resolve_content_curriculum — the fork→OOB swap ────────────────────────────


@pytest.mark.asyncio
async def test_plain_curriculum_is_not_swapped():
    with patch.object(svc, "get_unit_subject", AsyncMock(return_value="Mathematics")) as gus:
        cid, subject = await svc.resolve_content_curriculum(
            "G8-MATH-001", "curr-A", "school-1", pool=object()
        )
    assert cid == "curr-A"
    assert subject == "Mathematics"
    gus.assert_awaited_once()  # unit resolved directly; no fork lookup needed


@pytest.mark.asyncio
async def test_fork_swaps_to_oob_source():
    async def subject_by_curriculum(unit_id, curriculum_id, pool):
        # The fork has no units of its own; the source does.
        return None if curriculum_id == "fork-1" else "Science"

    with (
        patch.object(svc, "get_unit_subject", AsyncMock(side_effect=subject_by_curriculum)),
        patch.object(svc, "get_fork_source_curriculum", AsyncMock(return_value="default-2026-g8")),
    ):
        cid, subject = await svc.resolve_content_curriculum(
            "G8-SCI-001", "fork-1", "school-1", pool=object()
        )
    assert cid == "default-2026-g8"  # swapped
    assert subject == "Science"


@pytest.mark.asyncio
async def test_unresolvable_unit_returns_none_subject():
    with (
        patch.object(svc, "get_unit_subject", AsyncMock(return_value=None)),
        patch.object(svc, "get_fork_source_curriculum", AsyncMock(return_value=None)),
    ):
        cid, subject = await svc.resolve_content_curriculum(
            "nope", "fork-1", "school-1", pool=object()
        )
    assert subject is None
    assert cid == "fork-1"


# ── resolve_quiz_answer_key — override-first, then fork-swap + store ───────────


@pytest.mark.asyncio
async def test_override_wins_and_store_is_not_read():
    with (
        patch.object(svc, "get_active_override", AsyncMock(return_value=OVERRIDE_BODY)),
        patch.object(svc, "get_quiz_answer_key", AsyncMock(return_value=STORE_KEY)) as gk,
        patch.object(svc, "resolve_content_curriculum", AsyncMock()) as rcc,
    ):
        key = await svc.resolve_quiz_answer_key(
            "school-1", "fork-1", "G8-SCI-001", 1, "en", object(), object(), object()
        )
    # Assert the fields this test is ABOUT, not the whole dict. The point is that
    # the OVERRIDE supplied the verdict and the store was never read; the entry
    # also carries a stable_question_id since ADR-008 Phase 1, and an exact-equality
    # assertion on a growing structure fails for reasons unrelated to what it guards.
    assert key["q1"]["index"] == 1  # from override, not the store's 0
    assert key["q1"]["explanation"] == "override says B"
    gk.assert_not_awaited()  # store never read
    rcc.assert_not_awaited()  # no swap when the override answers


@pytest.mark.asyncio
async def test_fork_without_override_swaps_then_reads_store_under_source():
    with (
        patch.object(svc, "get_active_override", AsyncMock(return_value=None)),
        patch.object(
            svc,
            "resolve_content_curriculum",
            AsyncMock(return_value=("default-2026-g8", "Science")),
        ) as rcc,
        patch.object(svc, "get_quiz_answer_key", AsyncMock(return_value=STORE_KEY)) as gk,
    ):
        key = await svc.resolve_quiz_answer_key(
            "school-1", "fork-1", "G8-SCI-001", 2, "en", object(), object(), object()
        )
    assert key == STORE_KEY
    rcc.assert_awaited_once()
    # The store was read under the SWAPPED source id, not the fork (curriculum_id is
    # the first positional arg to get_quiz_answer_key).
    assert gk.await_args.args[0] == "default-2026-g8"


@pytest.mark.asyncio
async def test_non_school_student_reads_store_directly():
    with (
        patch.object(svc, "get_active_override", AsyncMock()) as gao,
        patch.object(svc, "resolve_content_curriculum", AsyncMock()) as rcc,
        patch.object(svc, "get_quiz_answer_key", AsyncMock(return_value=STORE_KEY)) as gk,
    ):
        key = await svc.resolve_quiz_answer_key(
            None, "default-2026-g8", "G8-SCI-001", 1, "en", object(), object(), object()
        )
    assert key == STORE_KEY
    gao.assert_not_awaited()  # no school → no override lookup
    rcc.assert_not_awaited()  # no school → no fork swap
    assert gk.await_args.args[0] == "default-2026-g8"
