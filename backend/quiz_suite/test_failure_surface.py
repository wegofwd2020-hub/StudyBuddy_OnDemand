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
