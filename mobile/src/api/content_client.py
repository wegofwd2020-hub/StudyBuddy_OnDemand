"""
mobile/src/api/content_client.py

Async HTTP client for content endpoints.

All calls go to {BACKEND_URL}/api/v1/content/{unit_id}/...

Layer rule: this module is in the api layer and only calls the backend REST API.
Never calls Anthropic directly.
"""

from __future__ import annotations

import os
from typing import Optional

import httpx

try:
    from mobile.config import BACKEND_URL  # type: ignore
except ImportError:
    BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")

from mobile.src.api import app_headers, version_headers  # noqa: E402


async def get_lesson(unit_id: str, token: str) -> dict:
    """
    Fetch the lesson for a unit from the backend.

    Returns the lesson JSON dict.
    Raises httpx.HTTPStatusError on non-2xx responses.
    """
    url = f"{BACKEND_URL}/api/v1/content/{unit_id}/lesson"
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(url, headers=app_headers(token))
        response.raise_for_status()
        return response.json()


async def get_quiz(unit_id: str, token: str) -> dict:
    """
    Fetch the next quiz set for a unit from the backend.
    The backend handles rotation (sets 1→2→3→1).
    """
    url = f"{BACKEND_URL}/api/v1/content/{unit_id}/quiz"
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(url, headers=app_headers(token))
        response.raise_for_status()
        return response.json()


async def get_tutorial(unit_id: str, token: str) -> dict:
    """Fetch the tutorial for a unit."""
    url = f"{BACKEND_URL}/api/v1/content/{unit_id}/tutorial"
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(url, headers=app_headers(token))
        response.raise_for_status()
        return response.json()


async def get_audio_url(unit_id: str, token: str) -> dict:
    """
    Fetch the audio URL for a unit lesson.

    Returns {url: str, expires_in: int}.
    The caller fetches the MP3 from the returned URL directly (CDN/S3).
    """
    url = f"{BACKEND_URL}/api/v1/content/{unit_id}/lesson/audio"
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(url, headers=app_headers(token))
        response.raise_for_status()
        return response.json()


async def get_app_version() -> dict:
    """
    Fetch the current min/latest app version from the backend.

    Returns {min_version: str, latest_version: str}.
    Called on app startup before login — no auth token required.
    The endpoint is unauthenticated; only X-App-Version is sent.
    """
    url = f"{BACKEND_URL}/api/v1/app/version"
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(url, headers=version_headers())
        response.raise_for_status()
        return response.json()


async def get_experiment(unit_id: str, token: str) -> dict:
    """
    Fetch the experiment for a unit.

    Returns the experiment JSON dict on HTTP 200.
    Raises httpx.HTTPStatusError with status_code 404 for non-lab units.
    Callers should catch 404 and hide the experiment button.
    """
    url = f"{BACKEND_URL}/api/v1/content/{unit_id}/experiment"
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(url, headers=app_headers(token))
        response.raise_for_status()
        return response.json()


async def report_content(
    unit_id: str,
    token: str,
    category: str,
    message: Optional[str] = None,
) -> None:
    """Submit a content report (incorrect, offensive, unclear, other)."""
    url = f"{BACKEND_URL}/api/v1/content/{unit_id}/report"
    payload = {"category": category}
    if message:
        payload["message"] = message

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(url, json=payload, headers=app_headers(token))
        response.raise_for_status()
