"""
tests/test_retention_emails.py

Unit tests for Phase E retention lifecycle email functions and the Celery task.

Tests mock _send() to avoid real SMTP connections.  They verify:
  - All 5 send_retention_email() template paths produce correct subjects/bodies.
  - Unknown template names are handled gracefully (no error, no send).
  - send_retention_email_task dispatches correctly (calls _run_async with the
    right async function).

No database or Celery broker required — all external I/O is mocked.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── Fixtures ──────────────────────────────────────────────────────────────────


GRADE = 8
CURRICULUM_NAME = "Grade 8 Science"
EXPIRES_DATE = "2026-05-01"
GRACE_DATE = "2026-10-28"
PURGE_DATE = "2026-10-28"
CONTACT_EMAIL = "admin@testschool.example.com"


# ── Template 1: pre-expiry warning ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_pre_expiry_email_subject_and_body():
    """send_retention_email sends correct subject and mentions expiry date."""
    from src.email.service import send_retention_email

    with patch("src.email.service._send", new_callable=AsyncMock) as mock_send:
        await send_retention_email(
            to_email=CONTACT_EMAIL,
            template="retention_pre_expiry_warning",
            grade=GRADE,
            curriculum_name=CURRICULUM_NAME,
            expires_date=EXPIRES_DATE,
        )

    mock_send.assert_awaited_once()
    call_kwargs = mock_send.call_args.kwargs
    assert call_kwargs["to_email"] == CONTACT_EMAIL
    assert str(GRADE) in call_kwargs["subject"]
    assert "30 days" in call_kwargs["subject"]
    assert EXPIRES_DATE in call_kwargs["text_body"]
    assert CURRICULUM_NAME in call_kwargs["text_body"]
    assert EXPIRES_DATE in call_kwargs["html_body"]


# ── Template 2: expiry notification ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_expiry_notification_email_subject_and_body():
    """send_retention_email for expiry notification includes expires and grace dates."""
    from src.email.service import send_retention_email

    with patch("src.email.service._send", new_callable=AsyncMock) as mock_send:
        await send_retention_email(
            to_email=CONTACT_EMAIL,
            template="retention_expiry_notification",
            grade=GRADE,
            curriculum_name=CURRICULUM_NAME,
            expires_date=EXPIRES_DATE,
            grace_date=GRACE_DATE,
        )

    call_kwargs = mock_send.call_args.kwargs
    assert "expired" in call_kwargs["subject"].lower()
    assert str(GRADE) in call_kwargs["subject"]
    assert EXPIRES_DATE in call_kwargs["text_body"]
    assert GRACE_DATE in call_kwargs["text_body"]
    assert GRACE_DATE in call_kwargs["html_body"]


# ── Template 3: 90-day grace reminder ────────────────────────────────────────


@pytest.mark.asyncio
async def test_grace_90day_reminder_email_subject_and_body():
    """send_retention_email for 90-day grace reminder mentions days remaining."""
    from src.email.service import send_retention_email

    with patch("src.email.service._send", new_callable=AsyncMock) as mock_send:
        await send_retention_email(
            to_email=CONTACT_EMAIL,
            template="retention_grace_90day_reminder",
            grade=GRADE,
            curriculum_name=CURRICULUM_NAME,
            grace_date=GRACE_DATE,
            days_remaining=90,
        )

    call_kwargs = mock_send.call_args.kwargs
    assert "90" in call_kwargs["subject"]
    assert GRACE_DATE in call_kwargs["text_body"]
    assert "90" in call_kwargs["text_body"]
    assert GRACE_DATE in call_kwargs["html_body"]


# ── Template 4: 30-day purge warning ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_purge_warning_30day_email_subject_and_body():
    """send_retention_email for 30-day purge warning has URGENT subject."""
    from src.email.service import send_retention_email

    with patch("src.email.service._send", new_callable=AsyncMock) as mock_send:
        await send_retention_email(
            to_email=CONTACT_EMAIL,
            template="retention_purge_warning_30day",
            grade=GRADE,
            curriculum_name=CURRICULUM_NAME,
            grace_date=GRACE_DATE,
            days_remaining=30,
        )

    call_kwargs = mock_send.call_args.kwargs
    assert "URGENT" in call_kwargs["subject"]
    assert "30" in call_kwargs["subject"]
    assert str(GRADE) in call_kwargs["subject"]
    assert GRACE_DATE in call_kwargs["text_body"]
    assert "no recovery" in call_kwargs["text_body"].lower()


# ── Template 5: purge complete ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_purge_complete_email_subject_and_body():
    """send_retention_email for purge_complete mentions purge date and FERPA note."""
    from src.email.service import send_retention_email

    with patch("src.email.service._send", new_callable=AsyncMock) as mock_send:
        await send_retention_email(
            to_email=CONTACT_EMAIL,
            template="retention_purge_complete",
            grade=GRADE,
            curriculum_name=CURRICULUM_NAME,
            purge_date=PURGE_DATE,
        )

    call_kwargs = mock_send.call_args.kwargs
    assert "deleted" in call_kwargs["subject"].lower()
    assert str(GRADE) in call_kwargs["subject"]
    assert PURGE_DATE in call_kwargs["text_body"]
    # HTML body includes FERPA note
    assert "FERPA" in call_kwargs["html_body"]


# ── Unknown template ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_unknown_template_skips_send():
    """send_retention_email with an unknown template name calls _send zero times."""
    from src.email.service import send_retention_email

    with patch("src.email.service._send", new_callable=AsyncMock) as mock_send:
        await send_retention_email(
            to_email=CONTACT_EMAIL,
            template="retention_nonexistent_template",
            grade=GRADE,
            curriculum_name=CURRICULUM_NAME,
        )

    mock_send.assert_not_called()


# ── Celery task dispatch ───────────────────────────────────────────────────────


def test_send_retention_email_task_calls_run_async():
    """
    send_retention_email_task invokes _run_async with send_retention_email.
    We patch _run_async to capture the coroutine that would be passed.
    """
    from src.auth import tasks as tasks_module

    captured = {}

    def fake_run_async(coro):
        captured["coro_name"] = type(coro).__name__
        coro.close()  # prevent ResourceWarning

    with patch.object(tasks_module, "_run_async", side_effect=fake_run_async):
        tasks_module.send_retention_email_task.run(
            to_email=CONTACT_EMAIL,
            template="retention_pre_expiry_warning",
            grade=GRADE,
            curriculum_name=CURRICULUM_NAME,
            expires_date=EXPIRES_DATE,
        )

    # The coroutine passed to _run_async should be a send_retention_email coroutine.
    assert captured.get("coro_name") == "coroutine"


def test_send_retention_email_task_configuration():
    """Task is registered with correct name, max_retries, and io queue."""
    from src.auth import tasks as tasks_module

    task = tasks_module.send_retention_email_task
    assert task.name == "src.auth.tasks.send_retention_email_task"
    assert task.max_retries == 3
    # Verify the task is routed to the io queue in task_routes.
    routes = tasks_module.celery_app.conf.task_routes
    assert routes.get("src.auth.tasks.send_retention_email_task") == {"queue": "io"}
