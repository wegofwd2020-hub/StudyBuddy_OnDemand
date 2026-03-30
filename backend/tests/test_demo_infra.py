"""
backend/tests/test_demo_infra.py

Tests for issue #33 — Demo foundation layer:
  - Migration: demo_requests, demo_verifications, demo_accounts tables exist
  - Email service: sends correct content, skips gracefully without SMTP config,
    raises on SMTP error
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

# ── Migration / schema tests ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_demo_requests_table_exists(db_conn):
    """demo_requests table is created by migration 0011."""
    row = await db_conn.fetchrow("SELECT to_regclass('public.demo_requests') AS t")
    assert row["t"] == "demo_requests"


@pytest.mark.asyncio
async def test_demo_verifications_table_exists(db_conn):
    """demo_verifications table is created by migration 0011."""
    row = await db_conn.fetchrow("SELECT to_regclass('public.demo_verifications') AS t")
    assert row["t"] == "demo_verifications"


@pytest.mark.asyncio
async def test_demo_accounts_table_exists(db_conn):
    """demo_accounts table is created by migration 0011."""
    row = await db_conn.fetchrow("SELECT to_regclass('public.demo_accounts') AS t")
    assert row["t"] == "demo_accounts"


@pytest.mark.asyncio
async def test_demo_requests_columns(db_conn):
    """demo_requests has the expected columns."""
    rows = await db_conn.fetch(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'demo_requests'
        ORDER BY column_name
        """
    )
    cols = {r["column_name"] for r in rows}
    assert {"id", "email", "ip_address", "user_agent", "status", "requested_at"} <= cols


@pytest.mark.asyncio
async def test_demo_verifications_columns(db_conn):
    """demo_verifications has the expected columns including token + expires_at."""
    rows = await db_conn.fetch(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'demo_verifications'
        ORDER BY column_name
        """
    )
    cols = {r["column_name"] for r in rows}
    assert {"id", "request_id", "email", "token", "expires_at", "used_at", "created_at"} <= cols


@pytest.mark.asyncio
async def test_demo_accounts_columns(db_conn):
    """demo_accounts has the expected operational columns."""
    rows = await db_conn.fetch(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'demo_accounts'
        ORDER BY column_name
        """
    )
    cols = {r["column_name"] for r in rows}
    assert {
        "id",
        "request_id",
        "student_id",
        "email",
        "password_hash",
        "expires_at",
        "created_at",
        "last_login_at",
        "extended_at",
        "extended_by",
        "revoked_at",
        "revoked_by",
    } <= cols


@pytest.mark.asyncio
async def test_demo_requests_status_constraint(db_conn):
    """demo_requests.status rejects invalid values."""
    with pytest.raises(Exception, match="demo_requests_status_check"):
        await db_conn.execute(
            "INSERT INTO demo_requests (email, status) VALUES ($1, $2)",
            "test@example.com",
            "invalid_status",
        )


@pytest.mark.asyncio
async def test_demo_requests_insert_and_fk_cascade(db_conn):
    """Inserting a demo_request and linking a verification works; cascade deletes."""
    import uuid
    from datetime import UTC, datetime, timedelta

    request_id = await db_conn.fetchval(
        "INSERT INTO demo_requests (email, ip_address, status) VALUES ($1, $2, $3) RETURNING id",
        "cascade@example.com",
        "127.0.0.1",
        "pending",
    )

    token = str(uuid.uuid4())
    expires = datetime.now(UTC) + timedelta(minutes=60)
    await db_conn.execute(
        """INSERT INTO demo_verifications (request_id, email, token, expires_at)
           VALUES ($1, $2, $3, $4)""",
        request_id,
        "cascade@example.com",
        token,
        expires,
    )

    # Cascade: deleting the request removes the verification
    await db_conn.execute("DELETE FROM demo_requests WHERE id=$1", request_id)
    count = await db_conn.fetchval(
        "SELECT COUNT(*) FROM demo_verifications WHERE request_id=$1", request_id
    )
    assert count == 0


# ── Email service tests ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_send_verification_email_skips_without_smtp(caplog):
    """send_verification_email logs a warning and does not raise when SMTP is unconfigured."""
    import src.email.service as svc

    with (
        patch.object(svc.settings, "SMTP_USER", None),
        patch.object(svc.settings, "SMTP_PASSWORD", None),
    ):
        # Should complete without raising
        await svc.send_verification_email("student@example.com", "test-token-abc123")


@pytest.mark.asyncio
async def test_send_credentials_email_skips_without_smtp():
    """send_credentials_email does not raise when SMTP is unconfigured."""
    import src.email.service as svc

    with (
        patch.object(svc.settings, "SMTP_USER", None),
        patch.object(svc.settings, "SMTP_PASSWORD", None),
    ):
        await svc.send_credentials_email("student@example.com", "TempPass-42!")


@pytest.mark.asyncio
async def test_send_verification_email_calls_aiosmtplib():
    """send_verification_email calls aiosmtplib.send with correct parameters."""
    import src.email.service as svc

    mock_send = AsyncMock(return_value=None)

    with (
        patch.object(svc.settings, "SMTP_USER", "hello@studybuddy.app"),
        patch.object(svc.settings, "SMTP_PASSWORD", "app-password-xyz"),
        patch.object(svc.settings, "SMTP_HOST", "smtp.gmail.com"),
        patch.object(svc.settings, "SMTP_PORT", 587),
        patch.object(svc.settings, "FRONTEND_URL", "https://app.studybuddy.com"),
        patch("src.email.service.aiosmtplib.send", mock_send),
    ):
        await svc.send_verification_email("student@example.com", "verify-token-999")

    mock_send.assert_awaited_once()
    call_kwargs = mock_send.call_args
    assert call_kwargs.kwargs["hostname"] == "smtp.gmail.com"
    assert call_kwargs.kwargs["port"] == 587
    assert call_kwargs.kwargs["start_tls"] is True


@pytest.mark.asyncio
async def test_send_verification_email_includes_token_url():
    """Verification email body contains the correct verification URL."""
    from email.mime.multipart import MIMEMultipart

    import src.email.service as svc

    captured: list[MIMEMultipart] = []

    async def _capture(msg, **kwargs):
        captured.append(msg)

    with (
        patch.object(svc.settings, "SMTP_USER", "hello@studybuddy.app"),
        patch.object(svc.settings, "SMTP_PASSWORD", "secret"),
        patch.object(svc.settings, "FRONTEND_URL", "https://app.studybuddy.com"),
        patch("src.email.service.aiosmtplib.send", _capture),
    ):
        await svc.send_verification_email("student@example.com", "token-xyz")

    assert len(captured) == 1
    msg = captured[0]
    # Decode each MIME part (parts may be base64-encoded)
    full_text = " ".join(
        part.get_payload(decode=True).decode("utf-8", errors="replace")
        for part in msg.get_payload()
    )
    assert "https://app.studybuddy.com/demo/verify/token-xyz" in full_text


@pytest.mark.asyncio
async def test_send_credentials_email_includes_password():
    """Credentials email body contains the generated password."""
    from email.mime.multipart import MIMEMultipart

    import src.email.service as svc

    captured: list[MIMEMultipart] = []

    async def _capture(msg, **kwargs):
        captured.append(msg)

    with (
        patch.object(svc.settings, "SMTP_USER", "hello@studybuddy.app"),
        patch.object(svc.settings, "SMTP_PASSWORD", "secret"),
        patch.object(svc.settings, "FRONTEND_URL", "https://app.studybuddy.com"),
        patch("src.email.service.aiosmtplib.send", _capture),
    ):
        await svc.send_credentials_email("student@example.com", "SuperSecret99!")

    assert len(captured) == 1
    msg = captured[0]
    full_text = " ".join(
        part.get_payload(decode=True).decode("utf-8", errors="replace")
        for part in msg.get_payload()
    )
    assert "SuperSecret99!" in full_text
    assert "student@example.com" in full_text
    assert "https://app.studybuddy.com/demo/login" in full_text


@pytest.mark.asyncio
async def test_send_email_raises_on_smtp_error():
    """_send propagates SMTPException when SMTP call fails."""
    import aiosmtplib

    import src.email.service as svc

    with (
        patch.object(svc.settings, "SMTP_USER", "hello@studybuddy.app"),
        patch.object(svc.settings, "SMTP_PASSWORD", "secret"),
        patch(
            "src.email.service.aiosmtplib.send",
            AsyncMock(side_effect=aiosmtplib.SMTPException("connection refused")),
        ),
    ):
        with pytest.raises(aiosmtplib.SMTPException):
            await svc.send_verification_email("fail@example.com", "bad-token")
