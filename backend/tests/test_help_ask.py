"""
backend/tests/test_help_ask.py

Tests for POST /api/v1/help/ask (Deliver-1 help RAG endpoint).

All external calls and retrieval functions are mocked so tests do not require
pgvector, Voyage AI, or Anthropic API keys, and are not affected by DB
transaction-isolation (the chunk retrieval never hits the live DB).

Mocked:
  - src.help.service._embed             → returns None (text-fallback path)
  - src.help.service._retrieve_by_text  → returns a deterministic fake record list
  - src.help.service._call_haiku        → returns a fixed structured string

For the no-chunks fallback test, _retrieve_by_text returns [].
"""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

# ── Shared test data ──────────────────────────────────────────────────────────

_FAKE_CHUNK = MagicMock()
_FAKE_CHUNK.__getitem__ = lambda self, key: {
    "chunk_id": "aaaaaaaa-0000-0000-0000-000000000001",
    "heading": "Provisioning a teacher",
    "body": "To add a teacher: go to School portal → Teachers → Add teacher.",
    "source_file": "help/school-admin/teachers.html",
    "section_id": "provision-teacher",
}[key]

_FAKE_HAIKU_RAW = """\
TITLE: Add a teacher to your school
STEPS:
1. Go to School portal → Teachers → Add teacher.
2. Enter the teacher's full name and email address.
3. Click Add teacher.
RESULT: ✓ The teacher receives a temporary password by email and can log in.
RELATED: Reset teacher password, Promote to admin, Assign grades
"""


@contextmanager
def _patch_retrieval(chunks=None):
    """Context manager that patches embed + text-retrieval + haiku."""
    if chunks is None:
        chunks = [_FAKE_CHUNK]
    with (
        patch("src.help.service._embed", new=AsyncMock(return_value=None)),
        patch("src.help.service._retrieve_by_text", new=AsyncMock(return_value=chunks)),
        patch("src.help.service._call_haiku", new=AsyncMock(return_value=_FAKE_HAIKU_RAW)) as mock_haiku,
    ):
        yield mock_haiku


# ── Valid requests ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_help_ask_school_admin_returns_structured_response(client: AsyncClient):
    """Valid school_admin question returns title, steps, result, related, sources."""
    with _patch_retrieval():
        r = await client.post("/api/v1/help/ask", json={
            "question": "How do I add a teacher?",
            "page": "/school/teachers",
            "role": "school_admin",
        })

    assert r.status_code == 200, r.text
    data = r.json()
    assert data["title"] == "Add a teacher to your school"
    assert isinstance(data["steps"], list)
    assert len(data["steps"]) == 3
    assert "Go to School portal" in data["steps"][0]
    assert data["result"].startswith("✓")
    assert isinstance(data["related"], list)
    assert len(data["related"]) == 3
    assert isinstance(data["sources"], list)
    assert data["sources"] == ["Provisioning a teacher"]


@pytest.mark.asyncio
async def test_help_ask_teacher_persona_returns_200(client: AsyncClient):
    """Valid teacher role question is accepted and returns 200."""
    with _patch_retrieval():
        r = await client.post("/api/v1/help/ask", json={
            "question": "How do I view student progress?",
            "role": "teacher",
        })

    assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_help_ask_student_persona_returns_200(client: AsyncClient):
    """Valid student role question is accepted and returns 200."""
    with _patch_retrieval():
        r = await client.post("/api/v1/help/ask", json={
            "question": "How do I take a quiz?",
            "role": "student",
        })

    assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_help_ask_page_is_optional(client: AsyncClient):
    """Omitting the page field is valid — the endpoint defaults to 'unknown'."""
    with _patch_retrieval():
        r = await client.post("/api/v1/help/ask", json={
            "question": "How do I add a teacher?",
            "role": "school_admin",
            # no "page" field
        })

    assert r.status_code == 200, r.text


# ── Validation errors ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_help_ask_empty_question_returns_422(client: AsyncClient):
    """A question shorter than 3 characters fails schema validation."""
    r = await client.post("/api/v1/help/ask", json={
        "question": "Hi",
        "role": "school_admin",
    })
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_help_ask_question_too_long_returns_422(client: AsyncClient):
    """A question exceeding 500 characters fails schema validation."""
    r = await client.post("/api/v1/help/ask", json={
        "question": "x" * 501,
        "role": "school_admin",
    })
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_help_ask_invalid_role_returns_422(client: AsyncClient):
    """An unknown role value is rejected with 422."""
    r = await client.post("/api/v1/help/ask", json={
        "question": "How do I manage billing?",
        "role": "superuser",
    })
    assert r.status_code == 422


# ── Fallback behaviour ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_help_ask_no_chunks_returns_graceful_fallback(client: AsyncClient):
    """When retrieval returns no chunks, the graceful fallback response is returned."""
    # No chunks → haiku must NOT be called.
    with (
        patch("src.help.service._embed", new=AsyncMock(return_value=None)),
        patch("src.help.service._retrieve_by_text", new=AsyncMock(return_value=[])),
        patch("src.help.service._call_haiku", new=AsyncMock(return_value=_FAKE_HAIKU_RAW)) as mock_haiku,
    ):
        r = await client.post("/api/v1/help/ask", json={
            "question": "How do I do something entirely unknown?",
            "role": "school_admin",
        })

    assert r.status_code == 200, r.text
    data = r.json()
    assert data["title"] == "I don't know"
    assert "support" in data["steps"][0].lower()
    mock_haiku.assert_not_called()
