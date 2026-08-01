"""
tests/test_progress.py

Tests for progress tracking endpoints.

Coverage:
  - POST /progress/session             — creates session, returns attempt_number
  - POST /progress/session/{id}/answer — ownership check, returns 200 immediately
  - POST /progress/session/{id}/end    — computes score/passed, 409 on double-end
  - GET  /progress/student             — returns history
  - Ownership enforcement: student B cannot touch student A's session
  - attempt_number is server-computed (not trusted from client)
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from tests.helpers.token_factory import make_student_token

# ── Helpers ───────────────────────────────────────────────────────────────────

# An 8-question quiz whose correct option is always index 0. Grading is exercised
# through the real endpoint; only the content-store lookup is stubbed.
_ANSWER_KEY_8Q = {
    f"q{i}": {"index": 0, "explanation": f"Because of reason {i}."} for i in range(1, 9)
}


async def _answer_all(
    client: AsyncClient, token: str, session_id: str, correct_count: int, total: int = 8
) -> None:
    """
    Answer `total` questions, getting the first `correct_count` of them right.

    Picks option 0 (correct per _ANSWER_KEY_8Q) or option 1 (wrong). The server
    decides which is which — the request never says.
    """
    for i in range(total):
        r = await client.post(
            f"/api/v1/progress/session/{session_id}/answer",
            json={
                "question_id": f"q{i + 1}",
                "student_answer": 0 if i < correct_count else 1,
                "ms_taken": 100,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200, r.text
        assert r.json()["correct"] is (i < correct_count)

async def _insert_student(client: AsyncClient, student_id: str) -> None:
    """Insert a minimal student row using the app pool (committed; visible to all connections)."""
    pool = client._transport.app.state.pool
    await pool.execute(
        """
        INSERT INTO students (student_id, external_auth_id, name, email, grade, locale, account_status)
        VALUES ($1, $2, $3, $4, 8, 'en', 'active')
        ON CONFLICT (student_id) DO NOTHING
        """,
        uuid.UUID(student_id),
        f"auth0|test-{student_id.replace('-', '')[:20]}",
        f"Test Student {student_id[:6]}",
        f"test-{student_id[:6]}@test.invalid",
    )


async def _start_session(client: AsyncClient, token: str) -> dict:
    r = await client.post(
        "/api/v1/progress/session",
        json={"unit_id": "G8-MATH-001", "curriculum_id": "default-2026-g8"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201, r.text
    return r.json()


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_start_session_returns_201(client, db_conn):
    """POST /progress/session creates a session and returns attempt_number = 1."""
    # Use a unique student ID to avoid leftover progress_sessions from earlier tests
    # (direct pool writes are committed and persist across the test session).
    import jose.jwt as _jwt
    token = make_student_token(student_id="f0000000-0000-0000-0000-000000000099")
    payload = _jwt.decode(token, "test-secret-do-not-use-in-production-aaaa", algorithms=["HS256"])
    student_id = payload["student_id"]

    await _insert_student(client, student_id)

    with patch("src.auth.tasks.celery_app.send_task", return_value=None):
        data = await _start_session(client, token)

    assert "session_id" in data
    assert data["unit_id"] == "G8-MATH-001"
    assert data["attempt_number"] == 1


@pytest.mark.asyncio
async def test_start_session_increments_attempt_number(client, db_conn):
    """Second session for the same unit has attempt_number = 2 after first is completed."""
    from jose import jwt as _jwt
    token = make_student_token(student_id="f1000000-0000-0000-0000-000000000098")
    payload = _jwt.decode(token, "test-secret-do-not-use-in-production-aaaa", algorithms=["HS256"])
    student_id = payload["student_id"]
    await _insert_student(client, student_id)

    with patch("src.auth.tasks.celery_app.send_task", return_value=None):
        s1 = await _start_session(client, token)
        # End session 1
        r = await client.post(
            f"/api/v1/progress/session/{s1['session_id']}/end",
            json={"score": 8, "total_questions": 8},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200

        s2 = await _start_session(client, token)
        assert s2["attempt_number"] == 2


@pytest.mark.asyncio
async def test_record_answer_returns_200(client, db_conn, student_token):
    """
    POST answer returns 200 with the SERVER's verdict.

    The server grades against the content store, so the answer key is stubbed
    (CI has no content on disk). The request sends only the picked option — the
    old `correct` / `correct_answer` fields are gone. q1's key says index 0, so
    picking 2 is graded wrong by the server regardless of what the client claims.
    """
    from jose import jwt as _jwt
    payload = _jwt.decode(student_token, "test-secret-do-not-use-in-production-aaaa", algorithms=["HS256"])
    student_id = payload["student_id"]
    await _insert_student(client, student_id)

    with patch("src.auth.tasks.celery_app.send_task", return_value=None), \
         patch("src.progress.router.get_quiz_answer_key", new_callable=AsyncMock,
               return_value=_ANSWER_KEY_8Q):
        session = await _start_session(client, student_token)
        r = await client.post(
            f"/api/v1/progress/session/{session['session_id']}/answer",
            json={
                "question_id": "q1",
                "student_answer": 2,
                "ms_taken": 3200,
            },
            headers={"Authorization": f"Bearer {student_token}"},
        )
    assert r.status_code == 200
    assert r.json()["correct"] is False
    assert r.json()["correct_index"] == 0


@pytest.mark.asyncio
async def test_answer_wrong_session_returns_404(client, db_conn, student_token):
    """Answering on a non-existent session_id returns 404."""
    fake_session_id = "c9000000-0000-0000-0000-000000000002"  # deterministic nonexistent ID
    from jose import jwt as _jwt
    payload = _jwt.decode(student_token, "test-secret-do-not-use-in-production-aaaa", algorithms=["HS256"])
    student_id = payload["student_id"]
    await _insert_student(client, student_id)

    with patch("src.auth.tasks.celery_app.send_task", return_value=None):
        r = await client.post(
            f"/api/v1/progress/session/{fake_session_id}/answer",
            json={"question_id": "q1", "student_answer": 1, "ms_taken": 500},
            headers={"Authorization": f"Bearer {student_token}"},
        )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_answer_other_student_session_returns_403(client, db_conn):
    """Student B cannot answer on Student A's session."""
    from jose import jwt as _jwt
    token_a = make_student_token(student_id="fa000000-0000-0000-0000-000000000010")
    token_b = make_student_token(student_id="fb000000-0000-0000-0000-000000000011")
    pa = _jwt.decode(token_a, "test-secret-do-not-use-in-production-aaaa", algorithms=["HS256"])
    pb = _jwt.decode(token_b, "test-secret-do-not-use-in-production-aaaa", algorithms=["HS256"])

    await _insert_student(client, pa["student_id"])
    await _insert_student(client, pb["student_id"])

    with patch("src.auth.tasks.celery_app.send_task", return_value=None):
        session_a = await _start_session(client, token_a)
        r = await client.post(
            f"/api/v1/progress/session/{session_a['session_id']}/answer",
            json={"question_id": "q1", "student_answer": 1, "ms_taken": 500},
            headers={"Authorization": f"Bearer {token_b}"},
        )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_end_session_computes_passed(client, db_conn, student_token):
    """
    Session end computes passed = True when score / total >= 0.6.

    The score comes from answers the server graded — the request body carries no
    score at all. Drive 6 correct + 2 wrong through /answer and expect 6/8.
    """
    from jose import jwt as _jwt
    payload = _jwt.decode(student_token, "test-secret-do-not-use-in-production-aaaa", algorithms=["HS256"])
    student_id = payload["student_id"]
    await _insert_student(client, student_id)

    with patch("src.auth.tasks.celery_app.send_task", return_value=None), \
         patch("src.progress.router.get_quiz_answer_key", new_callable=AsyncMock,
               return_value=_ANSWER_KEY_8Q):
        session = await _start_session(client, student_token)
        await _answer_all(client, student_token, session["session_id"], correct_count=6)
        r = await client.post(
            f"/api/v1/progress/session/{session['session_id']}/end",
            json={},
            headers={"Authorization": f"Bearer {student_token}"},
        )
    assert r.status_code == 200
    data = r.json()
    assert data["score"] == 6
    assert data["total_questions"] == 8
    assert data["passed"] is True  # 6/8 = 75% >= 60%


@pytest.mark.asyncio
async def test_client_cannot_inflate_its_own_score(client, db_conn, student_token):
    """
    A student who answers everything wrong and posts a perfect score still scores 0.

    This is the whole point of server-side grading: `correct` on the answer body
    and `score` on the end body used to be trusted verbatim.
    """
    from jose import jwt as _jwt
    payload = _jwt.decode(student_token, "test-secret-do-not-use-in-production-aaaa", algorithms=["HS256"])
    await _insert_student(client, payload["student_id"])

    with patch("src.auth.tasks.celery_app.send_task", return_value=None), \
         patch("src.progress.router.get_quiz_answer_key", new_callable=AsyncMock,
               return_value=_ANSWER_KEY_8Q):
        session = await _start_session(client, student_token)

        # Every answer wrong — and each request lies about it being correct.
        for i in range(8):
            r = await client.post(
                f"/api/v1/progress/session/{session['session_id']}/answer",
                json={
                    "question_id": f"q{i + 1}",
                    "student_answer": 3,      # key says 0 → wrong
                    "correct_answer": 3,      # ignored
                    "correct": True,          # ignored
                    "ms_taken": 10,
                },
                headers={"Authorization": f"Bearer {student_token}"},
            )
            assert r.status_code == 200
            assert r.json()["correct"] is False  # server overrules the client

        # ...and the end request claims a perfect score.
        r = await client.post(
            f"/api/v1/progress/session/{session['session_id']}/end",
            json={"score": 8, "total_questions": 8},
            headers={"Authorization": f"Bearer {student_token}"},
        )

    assert r.status_code == 200
    data = r.json()
    assert data["score"] == 0
    assert data["passed"] is False


@pytest.mark.asyncio
async def test_session_curriculum_is_resolved_server_side(client, db_conn):
    """
    The curriculum the session is graded against comes from the server, not the body.

    The web client used to send a hardcoded "default" here (#524). The session
    stored it verbatim and grading looked the answer key up under that id, which
    resolves to nothing in the content store — so every Submit 404'd and the quiz
    button went dead. Same rule as locale: authoritative from the JWT/server.
    """
    from jose import jwt as _jwt
    token = make_student_token(student_id="f2000000-0000-0000-0000-000000000097", grade=8)
    payload = _jwt.decode(token, "test-secret-do-not-use-in-production-aaaa", algorithms=["HS256"])
    await _insert_student(client, payload["student_id"])

    with patch("src.auth.tasks.celery_app.send_task", return_value=None):
        r = await client.post(
            "/api/v1/progress/session",
            json={"unit_id": "G8-MATH-001", "curriculum_id": "default"},  # client's claim
            headers={"Authorization": f"Bearer {token}"},
        )

    assert r.status_code == 201, r.text
    # Grade 8, no school → the STEM default package, NOT the "default" sent above.
    assert r.json()["curriculum_id"] == "default-2026-g8"


@pytest.mark.asyncio
async def test_grading_uses_the_resolved_curriculum_not_the_clients(client, db_conn):
    """
    The answer-key lookup is keyed by the resolved curriculum, whatever the client sent.

    Asserting on the kwarg rather than the response is deliberate: the previous
    tests all stubbed get_quiz_answer_key and never checked what it was called
    with, which is exactly how #524 shipped green.
    """
    from jose import jwt as _jwt
    token = make_student_token(student_id="f3000000-0000-0000-0000-000000000096", grade=8)
    payload = _jwt.decode(token, "test-secret-do-not-use-in-production-aaaa", algorithms=["HS256"])
    await _insert_student(client, payload["student_id"])

    captured: dict = {}

    async def _capture(**kwargs):
        captured.update(kwargs)
        return _ANSWER_KEY_8Q

    with patch("src.auth.tasks.celery_app.send_task", return_value=None), \
         patch("src.progress.router.get_quiz_answer_key", new=_capture):
        r = await client.post(
            "/api/v1/progress/session",
            json={"unit_id": "G8-MATH-001", "curriculum_id": "default"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 201, r.text
        session_id = r.json()["session_id"]

        r = await client.post(
            f"/api/v1/progress/session/{session_id}/answer",
            json={"question_id": "q1", "student_answer": 0, "ms_taken": 100},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert r.status_code == 200, r.text
    assert captured["curriculum_id"] == "default-2026-g8"


@pytest.mark.asyncio
async def test_start_session_without_curriculum_id_is_accepted(client, db_conn):
    """The field is optional — the client has no business supplying it at all."""
    from jose import jwt as _jwt
    token = make_student_token(student_id="f4000000-0000-0000-0000-000000000095", grade=8)
    payload = _jwt.decode(token, "test-secret-do-not-use-in-production-aaaa", algorithms=["HS256"])
    await _insert_student(client, payload["student_id"])

    with patch("src.auth.tasks.celery_app.send_task", return_value=None):
        r = await client.post(
            "/api/v1/progress/session",
            json={"unit_id": "G8-MATH-001"},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert r.status_code == 201, r.text
    assert r.json()["curriculum_id"] == "default-2026-g8"


@pytest.mark.asyncio
async def test_end_session_not_passed_below_threshold(client, db_conn, student_token):
    """Session end computes passed = False when score / total < 0.6."""
    from jose import jwt as _jwt
    payload = _jwt.decode(student_token, "test-secret-do-not-use-in-production-aaaa", algorithms=["HS256"])
    student_id = payload["student_id"]
    await _insert_student(client, student_id)

    with patch("src.auth.tasks.celery_app.send_task", return_value=None), \
         patch("src.progress.router.get_quiz_answer_key", new_callable=AsyncMock,
               return_value=_ANSWER_KEY_8Q):
        session = await _start_session(client, student_token)
        await _answer_all(client, student_token, session["session_id"], correct_count=4)
        r = await client.post(
            f"/api/v1/progress/session/{session['session_id']}/end",
            json={},
            headers={"Authorization": f"Bearer {student_token}"},
        )
    assert r.status_code == 200
    assert r.json()["passed"] is False  # 4/8 = 50% < 60%


@pytest.mark.asyncio
async def test_end_session_twice_returns_409(client, db_conn, student_token):
    """Ending the same session twice returns 409."""
    from jose import jwt as _jwt
    payload = _jwt.decode(student_token, "test-secret-do-not-use-in-production-aaaa", algorithms=["HS256"])
    student_id = payload["student_id"]
    await _insert_student(client, student_id)

    with patch("src.auth.tasks.celery_app.send_task", return_value=None):
        session = await _start_session(client, student_token)
        sid = session["session_id"]
        await client.post(
            f"/api/v1/progress/session/{sid}/end",
            json={"score": 8, "total_questions": 8},
            headers={"Authorization": f"Bearer {student_token}"},
        )
        r = await client.post(
            f"/api/v1/progress/session/{sid}/end",
            json={"score": 8, "total_questions": 8},
            headers={"Authorization": f"Bearer {student_token}"},
        )
    assert r.status_code == 409
    assert r.json()["error"] == "session_already_ended"


@pytest.mark.asyncio
async def test_get_history_returns_sessions(client, db_conn, student_token):
    """GET /progress/student returns list of sessions for the student."""
    from jose import jwt as _jwt
    payload = _jwt.decode(student_token, "test-secret-do-not-use-in-production-aaaa", algorithms=["HS256"])
    student_id = payload["student_id"]
    await _insert_student(client, student_id)

    with patch("src.auth.tasks.celery_app.send_task", return_value=None):
        await _start_session(client, student_token)
        r = await client.get(
            "/api/v1/progress/student",
            headers={"Authorization": f"Bearer {student_token}"},
        )
    assert r.status_code == 200
    data = r.json()
    assert data["student_id"] == student_id
    assert isinstance(data["sessions"], list)
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_progress_requires_auth(client):
    """Progress endpoints reject unauthenticated requests."""
    r = await client.post(
        "/api/v1/progress/session",
        json={"unit_id": "G8-MATH-001", "curriculum_id": "default-2026-g8"},
    )
    assert r.status_code == 401
