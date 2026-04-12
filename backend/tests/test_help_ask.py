"""
backend/tests/test_help_ask.py

Tests for POST /api/v1/help/ask (Deliver-1 + Deliver-3 help RAG endpoint).

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

_FAKE_INTERACTION_ID = "aaaaaaaa-1111-0000-0000-000000000001"


@contextmanager
def _patch_retrieval(chunks=None):
    """
    Context manager that patches embed + text-retrieval + haiku + log_interaction.

    log_interaction is mocked so tests never need a real help_interactions table.
    The mock returns a deterministic UUID so tests can assert on interaction_id.
    """
    if chunks is None:
        chunks = [_FAKE_CHUNK]
    with (
        patch("src.help.service._embed", new=AsyncMock(return_value=None)),
        patch("src.help.service._retrieve_by_text", new=AsyncMock(return_value=chunks)),
        patch("src.help.service._call_haiku", new=AsyncMock(return_value=_FAKE_HAIKU_RAW)) as mock_haiku,
        patch("src.help.router.log_interaction", new=AsyncMock(return_value=_FAKE_INTERACTION_ID)),
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
    # Deliver-4: interaction_id is returned for feedback submission.
    assert data["interaction_id"] == _FAKE_INTERACTION_ID


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


# ── Deliver-3: account_state context signals ──────────────────────────────────

@pytest.mark.asyncio
async def test_help_ask_account_state_accepted(client: AsyncClient):
    """Passing account_state is accepted and returns 200."""
    with _patch_retrieval():
        r = await client.post("/api/v1/help/ask", json={
            "question": "How do I set up my school?",
            "role": "school_admin",
            "account_state": {
                "teacher_count": 0,
                "student_count": 0,
                "classroom_count": 0,
                "curriculum_assigned": False,
            },
        })

    assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_help_ask_account_state_appears_in_prompt(client: AsyncClient):
    """Recognised account_state keys are rendered into the Haiku prompt."""
    with _patch_retrieval() as mock_haiku:
        r = await client.post("/api/v1/help/ask", json={
            "question": "What should I do first?",
            "role": "school_admin",
            "account_state": {
                "teacher_count": 0,
                "classroom_count": 2,
                "curriculum_assigned": False,
            },
        })

    assert r.status_code == 200, r.text
    # Verify account context was threaded into the prompt.
    prompt_sent = mock_haiku.call_args[0][0]
    assert "Teachers provisioned" in prompt_sent
    assert "Classrooms created" in prompt_sent
    assert "Curriculum package assigned" in prompt_sent


@pytest.mark.asyncio
async def test_help_ask_first_login_signal_in_prompt(client: AsyncClient):
    """first_login=True produces a descriptive account context line in the prompt."""
    with _patch_retrieval() as mock_haiku:
        r = await client.post("/api/v1/help/ask", json={
            "question": "How do I change my password?",
            "role": "teacher",
            "account_state": {"first_login": True},
        })

    assert r.status_code == 200, r.text
    prompt_sent = mock_haiku.call_args[0][0]
    assert "First login" in prompt_sent
    assert "temporary password" in prompt_sent


@pytest.mark.asyncio
async def test_help_ask_unknown_account_state_keys_ignored(client: AsyncClient):
    """Unknown account_state keys are silently ignored — no error, no prompt injection."""
    with _patch_retrieval() as mock_haiku:
        r = await client.post("/api/v1/help/ask", json={
            "question": "How do I add a teacher?",
            "role": "school_admin",
            "account_state": {
                "teacher_count": 3,
                "unknown_future_signal": "some_value",
                "another_unknown": 99,
            },
        })

    assert r.status_code == 200, r.text
    prompt_sent = mock_haiku.call_args[0][0]
    # Known key appears; unknown keys are absent from prompt.
    assert "Teachers provisioned" in prompt_sent
    assert "unknown_future_signal" not in prompt_sent
    assert "another_unknown" not in prompt_sent


@pytest.mark.asyncio
async def test_help_ask_omitting_account_state_still_works(client: AsyncClient):
    """Omitting account_state entirely is valid — no account context block in prompt."""
    with _patch_retrieval() as mock_haiku:
        r = await client.post("/api/v1/help/ask", json={
            "question": "How do I add a teacher?",
            "role": "school_admin",
            # no account_state
        })

    assert r.status_code == 200, r.text
    prompt_sent = mock_haiku.call_args[0][0]
    assert "Account context" not in prompt_sent


# ── Deliver-4: feedback endpoint ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_help_feedback_thumbs_up_returns_ok(client: AsyncClient):
    """POST /help/feedback with helpful=True returns {ok: true}."""
    fake_id = "bbbbbbbb-0000-0000-0000-000000000001"
    with patch("src.help.router.record_feedback", new=AsyncMock()) as mock_fb:
        r = await client.post("/api/v1/help/feedback", json={
            "interaction_id": fake_id,
            "helpful": True,
        })

    assert r.status_code == 200, r.text
    assert r.json()["ok"] is True
    mock_fb.assert_awaited_once()
    _, kwargs = mock_fb.call_args
    assert kwargs["helpful"] is True
    assert kwargs["interaction_id"] == fake_id


@pytest.mark.asyncio
async def test_help_feedback_thumbs_down_returns_ok(client: AsyncClient):
    """POST /help/feedback with helpful=False returns {ok: true}."""
    fake_id = "cccccccc-0000-0000-0000-000000000001"
    with patch("src.help.router.record_feedback", new=AsyncMock()):
        r = await client.post("/api/v1/help/feedback", json={
            "interaction_id": fake_id,
            "helpful": False,
        })

    assert r.status_code == 200, r.text
    assert r.json()["ok"] is True


@pytest.mark.asyncio
async def test_help_feedback_missing_interaction_id_returns_422(client: AsyncClient):
    """Omitting interaction_id fails schema validation."""
    r = await client.post("/api/v1/help/feedback", json={"helpful": True})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_help_feedback_wrong_id_length_returns_422(client: AsyncClient):
    """An interaction_id shorter than 36 chars fails schema validation."""
    r = await client.post("/api/v1/help/feedback", json={
        "interaction_id": "too-short",
        "helpful": True,
    })
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_help_ask_interaction_id_included_in_response(client: AsyncClient):
    """ask response always contains an interaction_id for the feedback loop."""
    with _patch_retrieval():
        r = await client.post("/api/v1/help/ask", json={
            "question": "How do I enrol a student?",
            "role": "teacher",
        })

    assert r.status_code == 200, r.text
    data = r.json()
    assert "interaction_id" in data
    assert data["interaction_id"] is not None
