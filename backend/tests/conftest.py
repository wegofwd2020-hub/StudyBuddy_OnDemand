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
# Force-assign JWT secrets so token_factory-signed tokens always verify correctly,
# even when running inside a container that has a different runtime secret set.
os.environ["JWT_SECRET"] = "test-secret-do-not-use-in-production-aaaa"
os.environ["ADMIN_JWT_SECRET"] = "test-admin-secret-do-not-use-in-prod-bbb"
os.environ["METRICS_TOKEN"] = "test-metrics-token"
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

# ── Test database URL ─────────────────────────────────────────────────────────
# Use a dedicated test DB so the downgrade/upgrade cycle is safe.
# TEST_DB_URL defaults to studybuddy_test on the same host as DATABASE_URL.
_dev_db_url = os.environ.get("DATABASE_URL", "postgresql://studybuddy:studybuddy_dev@db:5432/studybuddy")
TEST_DB_URL = os.environ.get(
    "TEST_DB_URL",
    _dev_db_url.replace("/studybuddy", "/studybuddy_test").replace("@pgbouncer:", "@db:"),
)


# ── Session-scoped: ensure test DB exists + run Alembic migrations ────────────

def _ensure_test_db(dev_url: str, test_url: str) -> None:
    """Create studybuddy_test if absent (requires connecting to the dev DB)."""
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

    # Extract DB name from test URL (last path segment).
    test_db_name = test_url.rstrip("/").rsplit("/", 1)[-1]
    # Connect to the dev DB as a superuser to issue CREATE DATABASE.
    conn_url = dev_url.replace("+asyncpg", "").replace("postgresql://", "postgresql+psycopg2://")
    # psycopg2 needs a plain postgresql:// URL without the driver prefix.
    plain_url = dev_url.replace("+asyncpg", "").replace("@pgbouncer:", "@db:")
    try:
        pg = psycopg2.connect(plain_url)
        pg.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        with pg.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (test_db_name,))
            if not cur.fetchone():
                cur.execute(f'CREATE DATABASE "{test_db_name}"')
        pg.close()
    except Exception:
        pass  # If creation fails, Alembic connect will surface the error.


@pytest.fixture(scope="session")
def event_loop():
    """Override default pytest-asyncio event loop to session scope."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
def run_migrations():
    """
    Ensure studybuddy_test exists, apply Alembic migrations, then tear down.

    Using a dedicated test DB means the downgrade is safe: it removes all
    schema from studybuddy_test without touching the dev DB.  Per-test data
    isolation is still provided by the db_conn transaction-rollback fixture.
    """
    from alembic import command
    from alembic.config import Config

    _ensure_test_db(_dev_db_url, TEST_DB_URL)

    # alembic/env.py reads TEST_DB_URL from the environment (takes precedence
    # over DATABASE_URL), so no need to override sqlalchemy.url manually here.
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")
    yield
    command.downgrade(cfg, "base")


# ── Per-test: fake Redis ──────────────────────────────────────────────────────

@pytest.fixture
def fake_redis():
    """In-memory fakeredis instance — no live Redis required."""
    return fakeredis.aioredis.FakeRedis(decode_responses=False)


# ── Per-test: asyncpg connection ──────────────────────────────────────────────

@pytest_asyncio.fixture
async def db_conn() -> AsyncGenerator[asyncpg.Connection, None]:
    """
    Provide an asyncpg connection to the test DB, wrapped in a transaction.

    Sets app.current_school_id = 'bypass' so that RLS policies (migration 0028)
    allow direct fixture inserts and reads without a teacher JWT in scope.
    Individual RLS isolation tests override this via a separate fixture.
    """
    conn = await asyncpg.connect(TEST_DB_URL)
    tr = conn.transaction()
    await tr.start()
    # 'true' = transaction-local; the value resets when the transaction rolls back.
    await conn.execute("SELECT set_config('app.current_school_id', 'bypass', true)")
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
    pool = await asyncpg.create_pool(TEST_DB_URL, min_size=1, max_size=5, statement_cache_size=0)
    app.state.pool = pool
    app.state.redis = fake_redis

    from config import settings as _cfg
    from src.core.storage import LocalStorage
    app.state.storage = LocalStorage(root=_cfg.CONTENT_STORE_PATH)

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
