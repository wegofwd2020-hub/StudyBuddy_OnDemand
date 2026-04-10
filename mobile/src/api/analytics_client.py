"""
mobile/src/api/analytics_client.py

Async HTTP client for analytics endpoints.

Routes:
  POST /api/v1/analytics/lesson/start  → start_lesson_view
  POST /api/v1/analytics/lesson/end    → end_lesson_view (sync, for SyncManager)

Layer rule: this module is in the api layer — only calls backend REST.
Never calls Anthropic or any AI service directly.
"""

from __future__ import annotations

import os

import httpx

try:
    from mobile.config import BACKEND_URL  # type: ignore
except ImportError:
    BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")

from mobile.src.api import app_headers  # noqa: E402


async def start_lesson_view(token: str, unit_id: str, curriculum_id: str) -> dict:
    """
    Notify the backend that a lesson was opened.

    Returns {view_id} — store this and pass it to end_lesson_view() on close.
    Raises httpx.HTTPStatusError on non-2xx responses.
    """
    url = f"{BACKEND_URL}/api/v1/analytics/lesson/start"
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            url,
            json={"unit_id": unit_id, "curriculum_id": curriculum_id},
            headers=app_headers(token),
        )
        response.raise_for_status()
        return response.json()


def end_lesson_view(
    token: str,
    view_id: str,
    duration_s: int,
    audio_played: bool = False,
    experiment_viewed: bool = False,
) -> dict:
    """
    Notify the backend that a lesson was closed.

    Synchronous — called by SyncManager when flushing queued lesson_end events.
    Returns {view_id, duration_s}.
    Raises httpx.HTTPStatusError on non-2xx responses.
    """
    url = f"{BACKEND_URL}/api/v1/analytics/lesson/end"
    response = httpx.post(
        url,
        json={
            "view_id": view_id,
            "duration_s": duration_s,
            "audio_played": audio_played,
            "experiment_viewed": experiment_viewed,
        },
        headers=app_headers(token),
        timeout=15,
    )
    response.raise_for_status()
    return response.json()
