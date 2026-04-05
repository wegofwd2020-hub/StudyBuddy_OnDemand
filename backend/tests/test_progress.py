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
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import AsyncClient

from tests.helpers.token_factory import make_student_token


# ── Helpers ───────────────────────────────────────────────────────────────────

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
        f"auth0|test-{student_id[:8]}",
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
async def test_start_session_returns_201(client, db_conn, student_token):
    """POST /progress/session creates a session and returns attempt_number = 1."""
    sid = make_student_token.__kwdefaults__  # not needed
    token = student_token
    from tests.helpers.token_factory import make_student_token as _make
    import jose.jwt as _jwt
    payload = _jwt.decode(token, "test-secret-do-not-use-in-production-aaaa", algorithms=["HS256"])
    student_id = payload["student_id"]

    await _insert_student(client, student_id)

    with patch("src.auth.tasks.celery_app.send_task", return_value=None):
        data = await _start_session(client, token)

    assert "session_id" in data
    assert data["unit_id"] == "G8-MATH-001"
    assert data["attempt_number"] == 1


@pytest.mark.asyncio
async def test_start_session_increments_attempt_number(client, db_conn, student_token):
    """Second session for the same unit has attempt_number = 2 after first is completed."""
    from jose import jwt as _jwt
    payload = _jwt.decode(student_token, "test-secret-do-not-use-in-production-aaaa", algorithms=["HS256"])
    student_id = payload["student_id"]
    await _insert_student(client, student_id)

    with patch("src.auth.tasks.celery_app.send_task", return_value=None):
        s1 = await _start_session(client, student_token)
        # End session 1
        r = await client.post(
            f"/api/v1/progress/session/{s1['session_id']}/end",
            json={"score": 8, "total_questions": 8},
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert r.status_code == 200

        s2 = await _start_session(client, student_token)
        assert s2["attempt_number"] == 2


@pytest.mark.asyncio
async def test_record_answer_returns_200(client, db_conn, student_token):
    """POST answer returns 200 immediately (fire-and-forget)."""
    from jose import jwt as _jwt
    payload = _jwt.decode(student_token, "test-secret-do-not-use-in-production-aaaa", algorithms=["HS256"])
    student_id = payload["student_id"]
    await _insert_student(client, student_id)

    with patch("src.auth.tasks.celery_app.send_task", return_value=None):
        session = await _start_session(client, student_token)
        r = await client.post(
            f"/api/v1/progress/session/{session['session_id']}/answer",
            json={
                "question_id": "q1",
                "student_answer": 2,
                "correct_answer": 1,
                "correct": False,
                "ms_taken": 3200,
            },
            headers={"Authorization": f"Bearer {student_token}"},
        )
    assert r.status_code == 200
    assert r.json()["correct"] is False


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
            json={"question_id": "q1", "student_answer": 1, "correct_answer": 1, "correct": True, "ms_taken": 500},
            headers={"Authorization": f"Bearer {student_token}"},
        )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_answer_other_student_session_returns_403(client, db_conn):
    """Student B cannot answer on Student A's session."""
    token_a = make_student_token()
    token_b = make_student_token()
    from jose import jwt as _jwt
    pa = _jwt.decode(token_a, "test-secret-do-not-use-in-production-aaaa", algorithms=["HS256"])
    pb = _jwt.decode(token_b, "test-secret-do-not-use-in-production-aaaa", algorithms=["HS256"])

    await _insert_student(client, pa["student_id"])
    await _insert_student(client, pb["student_id"])

    with patch("src.auth.tasks.celery_app.send_task", return_value=None):
        session_a = await _start_session(client, token_a)
        r = await client.post(
            f"/api/v1/progress/session/{session_a['session_id']}/answer",
            json={"question_id": "q1", "student_answer": 1, "correct_answer": 1, "correct": True, "ms_taken": 500},
            headers={"Authorization": f"Bearer {token_b}"},
        )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_end_session_computes_passed(client, db_conn, student_token):
    """Session end computes passed = True when score / total >= 0.6."""
    from jose import jwt as _jwt
    payload = _jwt.decode(student_token, "test-secret-do-not-use-in-production-aaaa", algorithms=["HS256"])
    student_id = payload["student_id"]
    await _insert_student(client, student_id)

    with patch("src.auth.tasks.celery_app.send_task", return_value=None):
        session = await _start_session(client, student_token)
        r = await client.post(
            f"/api/v1/progress/session/{session['session_id']}/end",
            json={"score": 6, "total_questions": 8},
            headers={"Authorization": f"Bearer {student_token}"},
        )
    assert r.status_code == 200
    data = r.json()
    assert data["score"] == 6
    assert data["total_questions"] == 8
    assert data["passed"] is True  # 6/8 = 75% >= 60%


@pytest.mark.asyncio
async def test_end_session_not_passed_below_threshold(client, db_conn, student_token):
    """Session end computes passed = False when score / total < 0.6."""
    from jose import jwt as _jwt
    payload = _jwt.decode(student_token, "test-secret-do-not-use-in-production-aaaa", algorithms=["HS256"])
    student_id = payload["student_id"]
    await _insert_student(client, student_id)

    with patch("src.auth.tasks.celery_app.send_task", return_value=None):
        session = await _start_session(client, student_token)
        r = await client.post(
            f"/api/v1/progress/session/{session['session_id']}/end",
            json={"score": 4, "total_questions": 8},
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
