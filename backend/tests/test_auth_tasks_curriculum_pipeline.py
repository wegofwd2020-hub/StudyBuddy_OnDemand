"""
tests/test_auth_tasks_curriculum_pipeline.py

Covers the main body of run_curriculum_pipeline_task in src/auth/tasks.py
(lines 762-895) — the 130-line per-unit build loop that PR #270 left
uncovered. PR #8 of Issue #261.

Scenarios:
  - Happy path: N units × 1 lang, all built → completed state + email dispatched
  - Partial failures: one unit returns status="failed" → completed_with_errors
  - SpendCapExceeded: break inner + outer loops; subsequent units not attempted
  - Individual unit Exception: captured into failed_units; loop continues
"""

from __future__ import annotations

import json
import sys
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _install_pipeline_stub() -> tuple[MagicMock, type]:
    """Install fake pipeline.build_unit + pipeline.config in sys.modules.

    Returns (build_unit_mod, SpendCapExceeded_class) so tests can mutate the
    mocked build_unit's return / side_effect and raise the real exception
    class the task's `except SpendCapExceeded` catches.
    """
    class _SpendCapExceeded(Exception):
        pass

    build_unit_mod = MagicMock()
    build_unit_mod.build_unit = MagicMock(return_value={"status": "built"})
    build_unit_mod.SpendCapExceeded = _SpendCapExceeded

    config_mod = MagicMock()
    config_mod.settings = MagicMock()

    sys.modules["pipeline"] = MagicMock()
    sys.modules["pipeline.build_unit"] = build_unit_mod
    sys.modules["pipeline.config"] = config_mod
    return build_unit_mod, _SpendCapExceeded


def _make_redis_job_client(initial: dict) -> MagicMock:
    """Sync Redis client holding a single pipeline:job key with in-memory store."""
    store: dict[str, str] = {"pipeline:job:fake-job": json.dumps(initial)}

    def _get(k):
        return store.get(k)

    def _setex(k, _ttl, v):
        store[k] = v

    r = MagicMock()
    r.get = MagicMock(side_effect=_get)
    r.setex = MagicMock(side_effect=_setex)
    r._store = store  # exposed for test-side inspection
    return r


def _units_conn(rows: list[dict], teacher_email: str | None) -> AsyncMock:
    """Single shared asyncpg conn used by both _fetch_units and _mark_done."""
    conn = AsyncMock()
    conn.fetch.return_value = rows
    conn.fetchrow.return_value = {"email": teacher_email} if teacher_email else None
    return conn


@pytest.fixture(autouse=True)
def _mock_send_pipeline_email_delay():
    """Prevent send_pipeline_email_task.delay from actually dispatching."""
    with patch("src.auth.tasks.send_pipeline_email_task.delay") as m:
        yield m


# ── Happy path ────────────────────────────────────────────────────────────────


def test_run_curriculum_pipeline_task_happy_path(_mock_send_pipeline_email_delay):
    from src.auth.tasks import run_curriculum_pipeline_task

    build_unit_mod, _ = _install_pipeline_stub()
    build_unit_mod.build_unit.return_value = {"status": "built"}

    units = [
        {"unit_id": "U1", "subject": "Math", "unit_name": "Algebra", "objectives": ["a", "b"], "has_lab": False},
        {"unit_id": "U2", "subject": "Math", "unit_name": "Geometry", "objectives": ["c"], "has_lab": True},
    ]
    conn = _units_conn(units, "teacher@example.com")
    redis_client = _make_redis_job_client({"status": "queued"})

    teacher_id = str(uuid.uuid4())
    with (
        patch("redis.from_url", return_value=redis_client),
        patch("asyncpg.connect", new=AsyncMock(return_value=conn)),
    ):
        run_curriculum_pipeline_task(
            job_id="fake-job",
            curriculum_id="cur-1",
            langs="en",
            force=False,
            teacher_id=teacher_id,
        )

    # build_unit called once per (unit, lang).
    assert build_unit_mod.build_unit.call_count == 2

    # _mark_done executes UPDATE curricula + one UPDATE per unit.
    update_sqls = [c.args[0] for c in conn.execute.await_args_list]
    assert any("UPDATE curricula SET status = $1" in s for s in update_sqls)
    unit_updates = [s for s in update_sqls if "UPDATE curriculum_units" in s]
    assert len(unit_updates) == 2

    # Final Redis state flips to completed + progress_pct=100.
    final = json.loads(redis_client._store["pipeline:job:fake-job"])
    assert final["status"] == "completed"
    assert final["progress_pct"] == 100.0
    assert final["built"] == 2

    # Teacher email dispatched once.
    _mock_send_pipeline_email_delay.assert_called_once_with(
        "teacher@example.com", "cur-1", 2, 0, []
    )


# ── Partial failures → completed_with_errors ──────────────────────────────────


def test_run_curriculum_pipeline_task_partial_failures(_mock_send_pipeline_email_delay):
    from src.auth.tasks import run_curriculum_pipeline_task

    build_unit_mod, _ = _install_pipeline_stub()
    # First unit builds; second returns status=failed.
    build_unit_mod.build_unit.side_effect = [
        {"status": "built"},
        {"status": "failed", "error": "validation error"},
    ]

    units = [
        {"unit_id": "U1", "subject": "Math", "unit_name": "A", "objectives": [], "has_lab": False},
        {"unit_id": "U2", "subject": "Math", "unit_name": "B", "objectives": [], "has_lab": False},
    ]
    conn = _units_conn(units, "teacher@example.com")
    redis_client = _make_redis_job_client({"status": "queued"})

    with (
        patch("redis.from_url", return_value=redis_client),
        patch("asyncpg.connect", new=AsyncMock(return_value=conn)),
    ):
        run_curriculum_pipeline_task(
            job_id="fake-job",
            curriculum_id="cur-1",
            langs="en",
            force=False,
            teacher_id=str(uuid.uuid4()),
        )

    final = json.loads(redis_client._store["pipeline:job:fake-job"])
    assert final["status"] == "completed_with_errors"
    assert final["built"] == 1
    assert final["failed"] == 1

    # _mark_done marks the curriculum 'failed' (any failed_units → failed).
    update_args = [c.args for c in conn.execute.await_args_list]
    curriculum_update = next(a for a in update_args if "UPDATE curricula" in a[0])
    assert curriculum_update[1] == "failed"

    # Failed unit details passed to the email task.
    _mock_send_pipeline_email_delay.assert_called_once()
    email_args = _mock_send_pipeline_email_delay.call_args.args
    # (teacher_email, curriculum_id, built, failed_count, failed_units)
    assert email_args[3] == 1
    assert email_args[4][0]["unit_id"] == "U2"


# ── SpendCapExceeded: stops dispatching further units ─────────────────────────


def test_run_curriculum_pipeline_task_spend_cap_breaks_loops(
    _mock_send_pipeline_email_delay,
):
    from src.auth.tasks import run_curriculum_pipeline_task

    build_unit_mod, SpendCapExceeded = _install_pipeline_stub()
    # First call succeeds; second raises SpendCapExceeded; third would
    # succeed but must NOT be reached because outer loop breaks.
    build_unit_mod.build_unit.side_effect = [
        {"status": "built"},
        SpendCapExceeded("monthly budget exhausted"),
        {"status": "built"},  # should never fire
    ]

    units = [
        {"unit_id": "U1", "subject": "M", "unit_name": "a", "objectives": [], "has_lab": False},
        {"unit_id": "U2", "subject": "M", "unit_name": "b", "objectives": [], "has_lab": False},
        {"unit_id": "U3", "subject": "M", "unit_name": "c", "objectives": [], "has_lab": False},
    ]
    # teacher_email is set so we can assert on the email-task args (the clearest
    # place to see the captured failed_units list after the spend-cap break).
    conn = _units_conn(units, "teacher@example.com")
    redis_client = _make_redis_job_client({"status": "queued"})

    with (
        patch("redis.from_url", return_value=redis_client),
        patch("asyncpg.connect", new=AsyncMock(return_value=conn)),
    ):
        run_curriculum_pipeline_task(
            job_id="fake-job",
            curriculum_id="cur-1",
            langs="en",
            force=False,
            teacher_id=str(uuid.uuid4()),
        )

    # build_unit called exactly twice — U3 never attempted after break.
    assert build_unit_mod.build_unit.call_count == 2

    # completed_with_errors because failed_units is non-empty.
    final = json.loads(redis_client._store["pipeline:job:fake-job"])
    assert final["status"] == "completed_with_errors"

    # Email-task args reveal the captured state: built=1, failed=1 (the U2
    # spend-cap entry). Final Redis state doesn't include the post-break
    # failed/built counters because the intermediate _update_job after U2 is
    # skipped by the break, so the email args are the clearest check.
    email_args = _mock_send_pipeline_email_delay.call_args.args
    assert email_args[2] == 1  # built
    assert email_args[3] == 1  # failed
    assert any("spend cap exceeded" in f["error"] for f in email_args[4])


# ── Per-unit arbitrary exception is captured, loop continues ──────────────────


def test_run_curriculum_pipeline_task_unit_exception_captured(
    _mock_send_pipeline_email_delay,
):
    from src.auth.tasks import run_curriculum_pipeline_task

    build_unit_mod, _ = _install_pipeline_stub()
    build_unit_mod.build_unit.side_effect = [
        RuntimeError("anthropic 500"),
        {"status": "built"},
    ]

    units = [
        {"unit_id": "U1", "subject": "M", "unit_name": "a", "objectives": [], "has_lab": False},
        {"unit_id": "U2", "subject": "M", "unit_name": "b", "objectives": [], "has_lab": False},
    ]
    conn = _units_conn(units, None)
    redis_client = _make_redis_job_client({"status": "queued"})

    with (
        patch("redis.from_url", return_value=redis_client),
        patch("asyncpg.connect", new=AsyncMock(return_value=conn)),
    ):
        run_curriculum_pipeline_task(
            job_id="fake-job",
            curriculum_id="cur-1",
            langs="en",
            force=False,
            teacher_id="",
        )

    # Both units attempted — exception on U1 didn't stop the loop.
    assert build_unit_mod.build_unit.call_count == 2

    final = json.loads(redis_client._store["pipeline:job:fake-job"])
    assert final["built"] == 1
    assert final["failed"] == 1
    assert final["status"] == "completed_with_errors"
