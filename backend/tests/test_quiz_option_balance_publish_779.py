"""
backend/tests/test_quiz_option_balance_publish_779.py

I-1 (final review, #779): `authoring_service.publish` writes accepted quiz
bodies straight from `authoring_topic_versions` to the content store. Versions
generated before #779 shipped are stored in the model's skewed order (or a
topic accepted before this shipped), and re-publish is allowed
(`status='published'` is accepted alongside `'generated'`) — so publishing
such a version undoes the store-wide rebalance. `publish` must run
`balance_options` on every `quiz_set_*` body before writing it.

`authoring_generation.generate_one` already balances at generation time (#779
shipped there first), so a project seeded through the normal generate path
never reproduces the pre-#779 skew we're guarding against here. This test
simulates a pre-#779 stored version by overwriting the active quiz_set_1
topic version's body directly with a skewed body, the same way an old row
would already be sitting in the database.
"""

from __future__ import annotations

import json
import os
import sys

import pytest
from httpx import AsyncClient
from main import app

from src.admin import authoring_service as svc
from tests.test_authoring_pr_b import _accept_all, _first_unit_id, _seed_generated_project

# run_analysis / generation lazily import the `pipeline` package (repo root).
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


def _skewed_quiz(set_number: int = 1) -> dict:
    """8 questions with distinct stems, every correct answer stored at "A" —
    the pre-#779 model habit this fix is guarding against."""
    questions = []
    for i in range(8):
        questions.append(
            {
                "question_id": f"q{i + 1}",
                "question_text": f"What is concept number {i + 1} in motion?",
                "question_type": "multiple_choice",
                "options": [
                    {"option_id": "A", "text": f"Correct answer {i + 1}"},
                    {"option_id": "B", "text": f"Wrong answer {i + 1}-1"},
                    {"option_id": "C", "text": f"Wrong answer {i + 1}-2"},
                    {"option_id": "D", "text": f"Wrong answer {i + 1}-3"},
                ],
                "correct_option": "A",
                "explanation": f"Because reason {i + 1}.",
                "difficulty": "easy",
            }
        )
    return {
        "unit_id": "U",
        "set_number": set_number,
        "language": "en",
        "questions": questions,
        "total_questions": 8,
        "estimated_duration_minutes": 10,
        "passing_score": 6,
        "generated_at": "2026-01-01T00:00:00Z",
        "model": "fake-model",
        "content_version": 1,
    }


async def _overwrite_active_quiz_body(
    pid: str, unit_id: str, content_type: str, body: dict
) -> None:
    """Overwrite the body of the currently-active topic version in place, the
    way a row already committed before #779 would look — bypassing the
    generation-time balance step entirely."""
    async with app.state.pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            UPDATE authoring_topic_versions tv SET body = $5
              FROM authoring_active_versions av
             WHERE av.topic_version_id = tv.topic_version_id
               AND av.project_id = $1 AND av.unit_id = $2
               AND av.content_type = $3 AND av.lang = $4
            """,
            pid,
            unit_id,
            content_type,
            "en",
            body,
        )


@pytest.mark.asyncio
async def test_publish_balances_skewed_quiz_options(client: AsyncClient) -> None:
    from config import settings

    pid = await _seed_generated_project()
    unit_id = _first_unit_id(pid)
    await _overwrite_active_quiz_body(pid, unit_id, "quiz_set_1", _skewed_quiz(1))
    await _accept_all(pid)

    async with app.state.pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        result = await svc.publish(conn, app.state.storage, pid, visibility="private")

    curriculum_id = result["curriculum_id"]
    path = os.path.join(
        settings.CONTENT_STORE_PATH, "curricula", curriculum_id, unit_id, "quiz_set_1_en.json"
    )
    with open(path, encoding="utf-8") as f:
        written = json.load(f)

    written_by_id = {q["question_id"]: q for q in written["questions"]}

    # (a) the written store copy is not still all-correct-at-A.
    assert {q["correct_option"] for q in written["questions"]} != {"A"}

    # (b) each question's correct answer TEXT is unchanged.
    for i in range(8):
        qid = f"q{i + 1}"
        q = written_by_id[qid]
        correct = next(o for o in q["options"] if o["option_id"] == q["correct_option"])
        assert correct["text"] == f"Correct answer {i + 1}"
