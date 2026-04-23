"""
tests/test_auth_dev_router.py

Unit tests for src/auth/dev_router.py — the development-only /auth/dev-login
endpoint.  Covers all 3 role branches (student / teacher / school_admin) and
the APP_ENV guard.

Part of Issue #261 coverage floor-raise: dev_router.py was at 0% coverage.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from httpx import AsyncClient

# ── APP_ENV guard ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_dev_login_forbidden_outside_development(client: AsyncClient):
    """Dev login MUST return 403 when APP_ENV != 'development'."""
    with patch("src.auth.dev_router.settings") as mock_settings:
        mock_settings.APP_ENV = "production"
        mock_settings.JWT_SECRET = "x" * 32

        r = await client.post("/api/v1/auth/dev-login", json={"role": "student"})

    assert r.status_code == 403
    detail = r.json()["detail"]
    assert detail["error"] == "forbidden"


@pytest.mark.asyncio
async def test_dev_login_forbidden_in_test_env(client: AsyncClient):
    """Test environment (APP_ENV='test') is not 'development', so dev login is forbidden."""
    with patch("src.auth.dev_router.settings") as mock_settings:
        mock_settings.APP_ENV = "test"
        mock_settings.JWT_SECRET = "x" * 32

        r = await client.post("/api/v1/auth/dev-login", json={"role": "teacher"})

    assert r.status_code == 403


# ── Role validation (before APP_ENV check) ────────────────────────────────────


@pytest.mark.asyncio
async def test_dev_login_rejects_invalid_role(client: AsyncClient):
    """Pydantic rejects any role not in {student, teacher, school_admin}."""
    r = await client.post("/api/v1/auth/dev-login", json={"role": "admin"})
    assert r.status_code == 422  # Pydantic validation, fires before handler


# ── Student, teacher, school_admin happy paths ────────────────────────────────


@pytest.mark.asyncio
async def test_dev_login_student_returns_token(client: AsyncClient, db_conn):
    """Student dev-login creates student + entitlement and returns JWT."""
    with patch("src.auth.dev_router.settings") as mock_settings:
        mock_settings.APP_ENV = "development"
        mock_settings.JWT_SECRET = "x" * 32

        r = await client.post("/api/v1/auth/dev-login", json={"role": "student"})

    assert r.status_code == 200, r.text
    data = r.json()
    assert data["role"] == "student"
    assert data["email"] == "dev.student@studybuddy.dev"
    assert data["name"] == "Dev Student"
    assert data["token"]  # non-empty


@pytest.mark.asyncio
async def test_dev_login_student_idempotent(client: AsyncClient, db_conn):
    """Second call returns a token for the existing dev student row (no duplicate insert)."""
    with patch("src.auth.dev_router.settings") as mock_settings:
        mock_settings.APP_ENV = "development"
        mock_settings.JWT_SECRET = "x" * 32

        r1 = await client.post("/api/v1/auth/dev-login", json={"role": "student"})
        r2 = await client.post("/api/v1/auth/dev-login", json={"role": "student"})

    assert r1.status_code == 200
    assert r2.status_code == 200
    # Both responses identify the same user
    assert r1.json()["email"] == r2.json()["email"]


@pytest.mark.asyncio
async def test_dev_login_teacher_returns_token(client: AsyncClient, db_conn):
    """Teacher dev-login creates dev school + teacher and returns JWT with teacher role."""
    with patch("src.auth.dev_router.settings") as mock_settings:
        mock_settings.APP_ENV = "development"
        mock_settings.JWT_SECRET = "x" * 32

        r = await client.post("/api/v1/auth/dev-login", json={"role": "teacher"})

    assert r.status_code == 200, r.text
    data = r.json()
    assert data["role"] == "teacher"
    assert data["email"] == "dev.teacher@studybuddy.dev"


@pytest.mark.asyncio
async def test_dev_login_school_admin_returns_token(client: AsyncClient, db_conn):
    """School-admin dev-login returns a JWT with role='school_admin'."""
    with patch("src.auth.dev_router.settings") as mock_settings:
        mock_settings.APP_ENV = "development"
        mock_settings.JWT_SECRET = "x" * 32

        r = await client.post("/api/v1/auth/dev-login", json={"role": "school_admin"})

    assert r.status_code == 200, r.text
    data = r.json()
    assert data["role"] == "school_admin"
    assert data["email"] == "dev.schooladmin@studybuddy.dev"
