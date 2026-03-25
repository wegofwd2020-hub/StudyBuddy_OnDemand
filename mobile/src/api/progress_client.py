"""
mobile/src/api/progress_client.py

Async HTTP client for progress and student endpoints.

Layer rule: this module is in the api layer — only calls backend REST.
Never calls Anthropic or any AI service directly.
"""

from __future__ import annotations

import os
from typing import Optional

import httpx

try:
    from mobile.config import BACKEND_URL  # type: ignore
except ImportError:
    BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Progress: session lifecycle ───────────────────────────────────────────────

async def start_session(token: str, unit_id: str, curriculum_id: str) -> dict:
    """
    Open a new quiz session.

    Returns StartSessionResponse: {session_id, unit_id, curriculum_id, attempt_number, started_at}
    """
    url = f"{BACKEND_URL}/api/v1/progress/session"
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            url,
            json={"unit_id": unit_id, "curriculum_id": curriculum_id},
            headers=_auth_headers(token),
        )
        response.raise_for_status()
        return response.json()


async def record_answer(
    token: str,
    session_id: str,
    question_id: str,
    student_answer: int,
    correct_answer: int,
    correct: bool,
    ms_taken: int,
    event_id: Optional[str] = None,
) -> dict:
    """
    Record a single answer during an active quiz session.

    Returns RecordAnswerResponse: {answer_id, correct}
    Write is fire-and-forget on the backend; returns immediately.
    """
    url = f"{BACKEND_URL}/api/v1/progress/session/{session_id}/answer"
    payload: dict = {
        "question_id": question_id,
        "student_answer": student_answer,
        "correct_answer": correct_answer,
        "correct": correct,
        "ms_taken": ms_taken,
    }
    if event_id:
        payload["event_id"] = event_id

    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(url, json=payload, headers=_auth_headers(token))
        response.raise_for_status()
        return response.json()


async def end_session(token: str, session_id: str, score: int, total_questions: int) -> dict:
    """
    Close a session and receive the backend-confirmed score.

    Returns EndSessionResponse: {session_id, score, total_questions, passed, attempt_number, ended_at}
    """
    url = f"{BACKEND_URL}/api/v1/progress/session/{session_id}/end"
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            url,
            json={"score": score, "total_questions": total_questions},
            headers=_auth_headers(token),
        )
        response.raise_for_status()
        return response.json()


async def get_progress_history(token: str, limit: int = 50, offset: int = 0) -> dict:
    """
    Fetch the student's full quiz history.

    Returns ProgressHistoryResponse: {student_id, sessions: [...], total}
    """
    url = f"{BACKEND_URL}/api/v1/progress/student"
    params = {"limit": limit, "offset": offset}
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(url, params=params, headers=_auth_headers(token))
        response.raise_for_status()
        return response.json()


# ── Student aggregates ────────────────────────────────────────────────────────

async def get_dashboard(token: str) -> dict:
    """
    Fetch the student dashboard summary.

    Returns DashboardResponse: {summary, subject_progress, next_unit, recent_activity}
    """
    url = f"{BACKEND_URL}/api/v1/student/dashboard"
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(url, headers=_auth_headers(token))
        response.raise_for_status()
        return response.json()


async def get_progress_map(token: str) -> dict:
    """
    Fetch the curriculum progress map with per-unit status badges.

    Returns ProgressMapResponse: {curriculum_id, pending_count, needs_retry_count, subjects}
    """
    url = f"{BACKEND_URL}/api/v1/student/progress"
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(url, headers=_auth_headers(token))
        response.raise_for_status()
        return response.json()


async def get_stats(token: str, period: str = "30d") -> dict:
    """
    Fetch usage statistics for the given period (7d | 30d | all).

    Returns StatsResponse: {period, lessons_viewed, quizzes_completed, ..., daily_activity}
    """
    url = f"{BACKEND_URL}/api/v1/student/stats"
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(url, params={"period": period}, headers=_auth_headers(token))
        response.raise_for_status()
        return response.json()
