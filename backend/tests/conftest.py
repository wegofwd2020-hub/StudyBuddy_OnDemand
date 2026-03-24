"""
backend/tests/conftest.py

Test fixtures for the StudyBuddy backend.

Strategy:
  - Uses asyncpg directly (no SQLAlchemy) for DB connections.
  - Applies Alembic migrations to studybuddy_test DB in a session-scoped fixture.
  - Uses fakeredis for Redis (no live Redis required in CI).
  - Overrides config settings with test values before importing the app.
  - Mocks Celery tasks to be no-ops.
  - Provides: client (httpx AsyncClient), db_conn (asyncpg), fake_redis,
              student_token, admin_token, teacher_token fixtures.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from typing import AsyncGenerator
from unittest.mock import AsyncMock, patch, MagicMock

import asyncpg
import fakeredis.aioredis
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# ── Override settings BEFORE importing main / config ─────────────────────────

os.environ.setdefault("DATABASE_URL", "postgresql://studybuddy:testpassword@localhost:5432/studybuddy_test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")
os.environ.setdefault("JWT_SECRET", "test-secret-do-not-use-in-production-aaaa")
os.environ.setdefault("ADMIN_JWT_SECRET", "test-admin-secret-do-not-use-in-prod-bbb")
os.environ.setdefault("AUTH0_DOMAIN", "test.auth0.com")
os.environ.setdefault("AUTH0_JWKS_URL", "http://localhost:9999/.well-known/jwks.json")
os.environ.setdefault("AUTH0_STUDENT_CLIENT_ID", "test-student-client-id")
os.environ.setdefault("AUTH0_TEACHER_CLIENT_ID", "test-teacher-client-id")
os.environ.setdefault("AUTH0_MGMT_CLIENT_ID", "test-mgmt-client-id")
os.environ.setdefault("AUTH0_MGMT_CLIENT_SECRET", "test-mgmt-client-secret-aaaaaaaaaaa")
os.environ.setdefault("AUTH0_MGMT_API_URL", "https://test.auth0.com/api/v2")
os.environ.setdefault("SENTRY_DSN", "")
os.environ.setdefault("METRICS_TOKEN", "test-metrics-token")
os.environ.setdefault("CONTENT_STORE_PATH", "/tmp/studybuddy-test-content")

# ── Now safe to import app ────────────────────────────────────────────────────

from main import app
from tests.helpers.token_factory import (
    TEST_ADMIN_JWT_SECRET,
    TEST_JWT_SECRET,
    make_admin_token,
    make_student_token,
    make_teacher_token,
)

TEST_DB_URL = os.environ["DATABASE_URL"]


# ── Session-scoped: run Alembic migrations once ───────────────────────────────

@pytest.fixture(scope="session")
def event_loop():
    """Override default pytest-asyncio event loop to session scope."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
def run_migrations():
    """Apply Alembic migrations to the test DB before any test runs."""
    from alembic import command
    from alembic.config import Config

    cfg = Config("alembic.ini")
    # Use synchronous psycopg2 URL for alembic.
    sync_url = TEST_DB_URL.replace("+asyncpg", "").replace(
        "postgresql://", "postgresql+psycopg2://"
    )
    if not sync_url.startswith("postgresql"):
        sync_url = TEST_DB_URL
    cfg.set_main_option("sqlalchemy.url", sync_url)

    try:
        command.upgrade(cfg, "head")
        yield
    finally:
        command.downgrade(cfg, "base")


# ── Per-test: fake Redis ──────────────────────────────────────────────────────

@pytest.fixture
def fake_redis():
    """In-memory fakeredis instance — no live Redis required."""
    return fakeredis.aioredis.FakeRedis(decode_responses=False)


# ── Per-test: asyncpg connection ──────────────────────────────────────────────

@pytest_asyncio.fixture
async def db_conn() -> AsyncGenerator[asyncpg.Connection, None]:
    """Provide an asyncpg connection to the test DB, wrapped in a transaction."""
    conn = await asyncpg.connect(TEST_DB_URL)
    tr = conn.transaction()
    await tr.start()
    try:
        yield conn
    finally:
        await tr.rollback()
        await conn.close()


# ── Per-test: HTTP client ─────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def client(fake_redis, db_conn) -> AsyncGenerator[AsyncClient, None]:
    """
    Provide an httpx AsyncClient backed by the FastAPI ASGI app.

    Injects a fake Redis and a real asyncpg pool (pointing to test DB).
    Mocks all Celery task dispatch to be no-ops.
    """
    pool = await asyncpg.create_pool(TEST_DB_URL, min_size=1, max_size=5)
    app.state.pool = pool
    app.state.redis = fake_redis

    with (
        patch("src.core.events.write_audit_log", return_value=None),
        patch("src.auth.tasks.write_audit_log_task.delay", return_value=None),
        patch("src.auth.tasks.sync_auth0_suspension.delay", return_value=None),
        patch("src.auth.tasks.cascade_school_suspension.delay", return_value=None),
        patch("src.auth.tasks.gdpr_delete_account.delay", return_value=None),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as c:
            yield c

    await pool.close()


# ── JWT token fixtures ────────────────────────────────────────────────────────

@pytest.fixture
def student_token() -> str:
    return make_student_token()


@pytest.fixture
def teacher_token() -> str:
    return make_teacher_token()


@pytest.fixture
def admin_token() -> str:
    return make_admin_token(role="super_admin")


@pytest.fixture
def product_admin_token() -> str:
    return make_admin_token(role="product_admin")


# ── Mock Celery globally ──────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def mock_celery_tasks():
    """Ensure Celery tasks never actually run in tests."""
    with (
        patch("src.auth.tasks.write_audit_log_task.delay", return_value=None),
        patch("src.auth.tasks.sync_auth0_suspension.delay", return_value=None),
        patch("src.auth.tasks.cascade_school_suspension.delay", return_value=None),
        patch("src.auth.tasks.gdpr_delete_account.delay", return_value=None),
    ):
        yield
