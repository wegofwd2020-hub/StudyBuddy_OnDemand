"""
tests/test_auth_tasks_identity.py

Identity / audit-cluster Celery tasks from src/auth/tasks.py.

Covers four zero-coverage tasks that sit on the auth critical path:
  - sync_auth0_suspension       — Auth0 block/unblock
  - cascade_school_suspension   — suspend all members of a school
  - gdpr_delete_account         — anonymise + delete from Auth0
  - write_audit_log_task        — append a row to audit_log

Part of Issue #261 floor-raise for src/auth. Each task is invoked directly
via the Celery .run() entry point with its async dependencies mocked at
their external module seams (no live Redis / Postgres / Auth0).
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _async_pool_ctx(pool: MagicMock) -> MagicMock:
    """Wrap a pool mock so `await asyncpg.create_pool(...)` returns it."""
    ctx = AsyncMock()
    ctx.return_value = pool
    return ctx


# ── sync_auth0_suspension ─────────────────────────────────────────────────────


def test_sync_auth0_suspension_block_calls_auth0_with_blocked_true():
    from src.auth.tasks import sync_auth0_suspension

    mock_redis = AsyncMock()
    with (
        patch("redis.asyncio.from_url", new=AsyncMock(return_value=mock_redis)),
        patch(
            "src.auth.auth0_client.block_auth0_user", new_callable=AsyncMock
        ) as mock_block,
    ):
        sync_auth0_suspension.run("auth0|user-123", "block")

    mock_block.assert_awaited_once_with(
        "auth0|user-123", blocked=True, redis=mock_redis
    )
    mock_redis.aclose.assert_awaited_once()


def test_sync_auth0_suspension_unblock_calls_auth0_with_blocked_false():
    from src.auth.tasks import sync_auth0_suspension

    mock_redis = AsyncMock()
    with (
        patch("redis.asyncio.from_url", new=AsyncMock(return_value=mock_redis)),
        patch(
            "src.auth.auth0_client.block_auth0_user", new_callable=AsyncMock
        ) as mock_block,
    ):
        sync_auth0_suspension.run("auth0|user-456", "unblock")

    mock_block.assert_awaited_once_with(
        "auth0|user-456", blocked=False, redis=mock_redis
    )


def test_sync_auth0_suspension_retries_on_auth0_error():
    from src.auth.tasks import sync_auth0_suspension

    mock_redis = AsyncMock()
    with (
        patch("redis.asyncio.from_url", new=AsyncMock(return_value=mock_redis)),
        patch(
            "src.auth.auth0_client.block_auth0_user",
            new_callable=AsyncMock,
            side_effect=RuntimeError("auth0 api down"),
        ),
    ):
        # `self.retry(...)` outside a worker raises; just assert it bubbles.
        with pytest.raises(Exception):
            sync_auth0_suspension.run("auth0|user-789", "block")


# ── cascade_school_suspension (retry path below) ──────────────────────────────


def test_cascade_school_suspension_noops_on_non_suspended_status():
    """Reactivating a school does not cascade to members — task returns early."""
    from src.auth.tasks import cascade_school_suspension

    mock_create_pool = AsyncMock()
    with patch("asyncpg.create_pool", mock_create_pool):
        cascade_school_suspension.run(str(uuid.uuid4()), "active")

    mock_create_pool.assert_not_called()


def test_cascade_school_suspension_suspends_teachers_and_students():
    from src.auth.tasks import cascade_school_suspension

    school_id = str(uuid.uuid4())
    teacher_id = uuid.uuid4()
    student_id = uuid.uuid4()

    pool = MagicMock()
    pool.fetch = AsyncMock(
        side_effect=[
            [{"teacher_id": teacher_id}],
            [{"student_id": student_id}],
        ]
    )
    pool.execute = AsyncMock()
    pool.close = AsyncMock()

    redis_pipeline = MagicMock()
    redis_pipeline.execute = AsyncMock()
    redis_client = AsyncMock()
    redis_client.pipeline = MagicMock(return_value=redis_pipeline)

    with (
        patch("asyncpg.create_pool", new=AsyncMock(return_value=pool)),
        patch("redis.asyncio.from_url", new=AsyncMock(return_value=redis_client)),
    ):
        cascade_school_suspension.run(school_id, "suspended")

    # Two SELECTs (teachers + students) + two UPDATEs (teachers + students).
    assert pool.fetch.await_count == 2
    assert pool.execute.await_count == 2

    # Redis pipeline set the suspension flag for each member.
    redis_pipeline.set.assert_any_call(f"suspended:{teacher_id}", "1")
    redis_pipeline.set.assert_any_call(f"suspended:{student_id}", "1")
    redis_pipeline.execute.assert_awaited_once()

    redis_client.aclose.assert_awaited_once()
    pool.close.assert_awaited_once()


# ── gdpr_delete_account ───────────────────────────────────────────────────────


def test_gdpr_delete_account_anonymises_student_and_deletes_auth0():
    from src.auth.tasks import gdpr_delete_account

    student_id = str(uuid.uuid4())
    auth0_sub = "auth0|to-delete-42"

    pool = MagicMock()
    pool.execute = AsyncMock()
    pool.close = AsyncMock()
    redis_client = AsyncMock()

    with (
        patch("asyncpg.create_pool", new=AsyncMock(return_value=pool)),
        patch("redis.asyncio.from_url", new=AsyncMock(return_value=redis_client)),
        patch(
            "src.auth.auth0_client.delete_auth0_user", new_callable=AsyncMock
        ) as mock_delete,
    ):
        gdpr_delete_account.run(student_id, auth0_sub)

    # DB anonymisation query fired with redacted placeholder values.
    pool.execute.assert_awaited_once()
    call_args = pool.execute.call_args.args
    assert "UPDATE students" in call_args[0]
    assert call_args[1] == f"deleted-{student_id[:8]}"  # anon_name
    assert call_args[2] == f"deleted-{student_id}@deleted.invalid"  # anon_email
    assert call_args[3] == uuid.UUID(student_id)

    mock_delete.assert_awaited_once_with(auth0_sub, redis=redis_client)
    redis_client.aclose.assert_awaited_once()
    pool.close.assert_awaited_once()


# ── write_audit_log_task ──────────────────────────────────────────────────────


def test_write_audit_log_task_inserts_row_with_all_fields():
    from src.auth.tasks import write_audit_log_task

    pool = MagicMock()
    pool.execute = AsyncMock()
    pool.close = AsyncMock()

    actor_id = str(uuid.uuid4())
    target_id = str(uuid.uuid4())

    with patch("asyncpg.create_pool", new=AsyncMock(return_value=pool)):
        write_audit_log_task.run(
            event_type="auth.suspend",
            actor_type="admin",
            actor_id=actor_id,
            target_type="student",
            target_id=target_id,
            metadata={"reason": "policy"},
            ip_address="10.0.0.1",
            correlation_id="corr-xyz",
        )

    pool.execute.assert_awaited_once()
    call_args = pool.execute.call_args.args
    assert "INSERT INTO audit_log" in call_args[0]
    assert call_args[1] == "auth.suspend"
    assert call_args[2] == "admin"
    assert call_args[3] == uuid.UUID(actor_id)
    assert call_args[4] == "student"
    assert call_args[5] == uuid.UUID(target_id)
    assert call_args[6] == '{"reason": "policy"}'  # json-encoded
    assert call_args[7] == "10.0.0.1"
    assert call_args[8] == "corr-xyz"
    pool.close.assert_awaited_once()


def test_write_audit_log_task_handles_null_optional_fields():
    """actor_id / target_id / metadata = None — no uuid.UUID() call, no JSON encode."""
    from src.auth.tasks import write_audit_log_task

    pool = MagicMock()
    pool.execute = AsyncMock()
    pool.close = AsyncMock()

    with patch("asyncpg.create_pool", new=AsyncMock(return_value=pool)):
        write_audit_log_task.run(
            event_type="system.startup",
            actor_type="system",
            actor_id=None,
            target_type=None,
            target_id=None,
            metadata=None,
            ip_address=None,
            correlation_id=None,
        )

    call_args = pool.execute.call_args.args
    assert call_args[3] is None  # actor_id
    assert call_args[5] is None  # target_id
    assert call_args[6] is None  # metadata


# ── Retry paths ───────────────────────────────────────────────────────────────


def test_cascade_school_suspension_retries_on_db_error():
    from src.auth.tasks import cascade_school_suspension

    with patch(
        "asyncpg.create_pool",
        new=AsyncMock(side_effect=RuntimeError("db down")),
    ):
        with pytest.raises(Exception):
            cascade_school_suspension.run(str(uuid.uuid4()), "suspended")


def test_gdpr_delete_account_retries_on_db_error():
    from src.auth.tasks import gdpr_delete_account

    with patch(
        "asyncpg.create_pool",
        new=AsyncMock(side_effect=RuntimeError("db down")),
    ):
        with pytest.raises(Exception):
            gdpr_delete_account.run(str(uuid.uuid4()), "auth0|user-x")


def test_write_audit_log_task_retries_on_db_error():
    from src.auth.tasks import write_audit_log_task

    with patch(
        "asyncpg.create_pool",
        new=AsyncMock(side_effect=RuntimeError("db down")),
    ):
        with pytest.raises(Exception):
            write_audit_log_task.run(
                event_type="test",
                actor_type="system",
                actor_id=None,
                target_type=None,
                target_id=None,
                metadata=None,
                ip_address=None,
                correlation_id=None,
            )
