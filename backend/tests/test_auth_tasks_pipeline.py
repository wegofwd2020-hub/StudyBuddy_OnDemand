"""
tests/test_auth_tasks_pipeline.py

Pipeline-cluster Celery tasks from src/auth/tasks.py. PR #5 of Issue #261.

Covers four zero-coverage tasks on the content-generation path:
  - send_pipeline_email_task      — teacher notification on job completion
  - regenerate_subject_task       — pipeline re-build of one subject
  - run_curriculum_pipeline_task  — school-owned curriculum end-to-end build
  - run_grade_pipeline_task       — default-grade end-to-end build

The two end-to-end tasks (run_*) are deliberately covered at the shape
level rather than line-by-line: their 100+ LOC bodies stitch together
asyncpg + redis + pipeline.build_* with spend-cap / import-fail
fall-throughs that are better exercised as integration tests. Tests
here assert the happy path + the failure modes we want to survive
(broker Redis down → status flipped to "error"; missing pipeline deps
on a non-pipeline worker → graceful exit without crash).
"""

from __future__ import annotations

import json
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── send_pipeline_email_task ──────────────────────────────────────────────────


def test_send_pipeline_email_task_sends_via_sendgrid_when_key_present():
    from src.auth.tasks import send_pipeline_email_task

    with (
        patch("src.auth.tasks.settings.SENDGRID_API_KEY", "sg-key"),
        patch("src.auth.tasks.settings.EMAIL_FROM", "noreply@studybuddy.app"),
        patch("httpx.post") as mock_post,
    ):
        send_pipeline_email_task(
            teacher_email="teacher@school.example",
            curriculum_id="cur-123",
            built=18,
            failed=0,
            failed_units=[],
        )

    mock_post.assert_called_once()
    url, = mock_post.call_args.args
    assert url == "https://api.sendgrid.com/v3/mail/send"
    payload = mock_post.call_args.kwargs["json"]
    assert payload["personalizations"][0]["to"][0]["email"] == "teacher@school.example"
    assert "18 built" in payload["subject"]
    assert mock_post.call_args.kwargs["headers"]["Authorization"] == "Bearer sg-key"


def test_send_pipeline_email_task_skips_send_when_key_missing():
    from src.auth.tasks import send_pipeline_email_task

    with (
        patch("src.auth.tasks.settings.SENDGRID_API_KEY", None),
        patch("httpx.post") as mock_post,
    ):
        send_pipeline_email_task(
            teacher_email="teacher@school.example",
            curriculum_id="cur-123",
            built=5,
            failed=0,
            failed_units=[],
        )

    mock_post.assert_not_called()


def test_send_pipeline_email_task_renders_failure_summary():
    """failed > 0 → subject reflects failures; body lists failed units."""
    from src.auth.tasks import send_pipeline_email_task

    with (
        patch("src.auth.tasks.settings.SENDGRID_API_KEY", "sg-key"),
        patch("src.auth.tasks.settings.EMAIL_FROM", "noreply@studybuddy.app"),
        patch("httpx.post") as mock_post,
    ):
        send_pipeline_email_task(
            teacher_email="teacher@school.example",
            curriculum_id="cur-123",
            built=15,
            failed=2,
            failed_units=[
                {"unit_id": "U1", "error": "quota exceeded"},
                {"unit_id": "U2", "error": "validation failed"},
            ],
        )

    payload = mock_post.call_args.kwargs["json"]
    assert "2 failure(s)" in payload["subject"]
    body = payload["content"][0]["value"]
    assert "U1: quota exceeded" in body
    assert "U2: validation failed" in body


def test_send_pipeline_email_task_swallows_sendgrid_errors():
    """httpx error → logged warning, no raise (fire-and-forget)."""
    from src.auth.tasks import send_pipeline_email_task

    with (
        patch("src.auth.tasks.settings.SENDGRID_API_KEY", "sg-key"),
        patch("src.auth.tasks.settings.EMAIL_FROM", "noreply@studybuddy.app"),
        patch("httpx.post", side_effect=RuntimeError("sendgrid 503")),
    ):
        # Must not raise — notification is best-effort.
        send_pipeline_email_task(
            teacher_email="t@s.example",
            curriculum_id="cur-1",
            built=1,
            failed=0,
            failed_units=[],
        )


# ── regenerate_subject_task ───────────────────────────────────────────────────


def _install_pipeline_stub_modules() -> tuple[MagicMock, MagicMock]:
    """Install fake pipeline.build_unit + pipeline.config modules in sys.modules.

    run_curriculum_pipeline_task and regenerate_subject_task import these lazily
    at task-execution time; on a non-pipeline worker they're genuinely absent.
    For unit tests we stub them so the import resolves and the task body runs.
    """
    build_unit_mod = MagicMock()
    build_unit_mod.build_unit = MagicMock(return_value={"status": "built"})

    # SpendCapExceeded is caught by an `except` in run_curriculum_pipeline_task;
    # it must be a real exception class.
    class _SpendCapExceeded(Exception):
        pass

    build_unit_mod.SpendCapExceeded = _SpendCapExceeded

    config_mod = MagicMock()
    config_mod.settings = MagicMock(CONTENT_STORE_PATH="/tmp/content")

    sys.modules["pipeline"] = MagicMock()
    sys.modules["pipeline.build_unit"] = build_unit_mod
    sys.modules["pipeline.config"] = config_mod
    return build_unit_mod, config_mod


def test_regenerate_subject_task_builds_every_unit_in_subject():
    from src.auth.tasks import regenerate_subject_task

    build_unit_mod, _ = _install_pipeline_stub_modules()
    build_unit_mod.build_unit.return_value = {"status": "ok"}

    pool = MagicMock()
    pool.fetch = AsyncMock(
        return_value=[
            {"unit_id": "U1", "title": "Algebra I", "description": "intro", "has_lab": False},
            {"unit_id": "U2", "title": "Algebra II", "description": "", "has_lab": True},
        ]
    )
    pool.close = AsyncMock()

    with patch("asyncpg.create_pool", new=AsyncMock(return_value=pool)):
        regenerate_subject_task.run(curriculum_id="default-2026-g8", subject="Mathematics")

    assert build_unit_mod.build_unit.call_count == 2
    for call in build_unit_mod.build_unit.call_args_list:
        assert call.kwargs["curriculum_id"] == "default-2026-g8"
        assert call.kwargs["lang"] == "en"
        assert call.kwargs["force"] is True
    pool.close.assert_awaited_once()


def test_regenerate_subject_task_retries_on_db_error():
    from src.auth.tasks import regenerate_subject_task

    _install_pipeline_stub_modules()

    with patch(
        "asyncpg.create_pool",
        new=AsyncMock(side_effect=RuntimeError("pool timeout")),
    ):
        with pytest.raises(Exception):
            regenerate_subject_task.run(curriculum_id="cur-1", subject="CS")


# ── run_curriculum_pipeline_task ──────────────────────────────────────────────


def _make_redis_job_client(job_state: dict) -> MagicMock:
    """Mock sync redis client holding a single pipeline:job:{id} key."""
    store = {"pipeline:job:fake-job": json.dumps(job_state)}

    def _get(key):
        return store.get(key)

    def _setex(key, _ttl, value):
        store[key] = value

    r = MagicMock()
    r.get = MagicMock(side_effect=_get)
    r.setex = MagicMock(side_effect=_setex)
    return r


def test_run_curriculum_pipeline_task_exception_path_updates_job_status():
    """If anything above the main try/except raises, the job is flipped to 'error'."""
    from src.auth.tasks import run_curriculum_pipeline_task

    _install_pipeline_stub_modules()

    redis_client = _make_redis_job_client({"status": "queued"})

    # Force an early failure by making asyncpg.connect (used inside _fetch_units) raise.
    with (
        patch("redis.from_url", return_value=redis_client),
        patch("asyncpg.connect", new=AsyncMock(side_effect=RuntimeError("db unreachable"))),
    ):
        # Must not raise — the outer except swallows and updates job state.
        run_curriculum_pipeline_task(
            job_id="fake-job",
            curriculum_id="cur-1",
            langs="en",
            force=False,
            teacher_id="00000000-0000-0000-0000-000000000000",
        )

    # The final setex call wrote status="error" into the job state.
    last_write = redis_client.setex.call_args_list[-1].args[2]
    assert json.loads(last_write)["status"] == "error"


def test_run_curriculum_pipeline_task_noop_when_job_state_missing():
    """If the pipeline:job:{id} key is absent, _update_job is a no-op; task must not crash."""
    from src.auth.tasks import run_curriculum_pipeline_task

    _install_pipeline_stub_modules()

    r = MagicMock()
    r.get = MagicMock(return_value=None)  # no job state in Redis
    r.setex = MagicMock()

    with (
        patch("redis.from_url", return_value=r),
        patch("asyncpg.connect", new=AsyncMock(side_effect=RuntimeError("stop here"))),
    ):
        # Must not raise even though job state is absent and DB fails.
        run_curriculum_pipeline_task(
            job_id="missing-job",
            curriculum_id="cur-x",
            langs="en",
            force=False,
            teacher_id="",
        )

    # setex should never be called because _update_job exits early on missing key.
    r.setex.assert_not_called()


# ── run_grade_pipeline_task ───────────────────────────────────────────────────


def test_run_grade_pipeline_task_happy_path_marks_job_completed():
    """run_grade() returns a success summary → Redis job state flips to 'completed'."""
    from src.auth.tasks import run_grade_pipeline_task

    # Stub pipeline.build_grade.run_grade + pipeline.config
    build_grade_mod = MagicMock()
    build_grade_mod.run_grade = MagicMock(
        return_value={
            "total_units": 12,
            "succeeded": 12,
            "failed": 0,
            "total_tokens": 100000,
            "total_cost_usd": 1.2,
            "duration_ms": 60000,
        }
    )
    config_mod = MagicMock()
    config_mod.settings = MagicMock(CONTENT_STORE_PATH="/tmp/content", REVIEW_AUTO_APPROVE=True)
    sys.modules["pipeline"] = MagicMock()
    sys.modules["pipeline.build_grade"] = build_grade_mod
    sys.modules["pipeline.config"] = config_mod

    redis_client = _make_redis_job_client({"status": "queued"})

    # asyncpg.connect is awaited for _mark_started / _mark_done; return a
    # connection that accepts execute/close.
    conn = AsyncMock()

    with (
        patch("redis.from_url", return_value=redis_client),
        patch("asyncpg.connect", new=AsyncMock(return_value=conn)),
    ):
        run_grade_pipeline_task(
            job_id="fake-job",
            grade=8,
            langs="en",
            force=False,
            year=2026,
            stream=None,
        )

    build_grade_mod.run_grade.assert_called_once()
    # Final state write has status=completed.
    final_write = json.loads(redis_client.setex.call_args_list[-1].args[2])
    assert final_write["status"] == "completed"
    assert final_write["built"] == 12
    assert final_write["failed"] == 0


def test_run_grade_pipeline_task_handles_pipeline_import_failure():
    """pipeline.build_grade unavailable (non-pipeline worker) → job marked failed, no raise."""
    from src.auth.tasks import run_grade_pipeline_task

    # Remove any stub so the import actually fails.
    for k in ("pipeline", "pipeline.build_grade", "pipeline.config"):
        sys.modules.pop(k, None)

    redis_client = _make_redis_job_client({"status": "queued"})

    import builtins

    original_import = builtins.__import__

    def _raising_import(name, *args, **kwargs):
        if name.startswith("pipeline.build_grade") or name == "pipeline.build_grade":
            raise ImportError("pipeline deps missing on this worker")
        return original_import(name, *args, **kwargs)

    with (
        patch("redis.from_url", return_value=redis_client),
        patch("builtins.__import__", side_effect=_raising_import),
    ):
        run_grade_pipeline_task(
            job_id="fake-job",
            grade=8,
            langs="en",
            force=False,
            year=2026,
        )

    # Job state must reflect the import failure.
    final_write = json.loads(redis_client.setex.call_args_list[-1].args[2])
    assert final_write["status"] == "failed"
    assert "pipeline deps missing" in final_write.get("error", "")


def test_run_grade_pipeline_task_run_grade_exception_marks_job_failed():
    """run_grade() raises → outer except flips job to 'failed' + writes error string."""
    from src.auth.tasks import run_grade_pipeline_task

    build_grade_mod = MagicMock()
    build_grade_mod.run_grade = MagicMock(side_effect=RuntimeError("anthropic 429"))
    config_mod = MagicMock()
    config_mod.settings = MagicMock(CONTENT_STORE_PATH="/tmp/content", REVIEW_AUTO_APPROVE=True)
    sys.modules["pipeline"] = MagicMock()
    sys.modules["pipeline.build_grade"] = build_grade_mod
    sys.modules["pipeline.config"] = config_mod

    redis_client = _make_redis_job_client({"status": "queued"})
    conn = AsyncMock()

    with (
        patch("redis.from_url", return_value=redis_client),
        patch("asyncpg.connect", new=AsyncMock(return_value=conn)),
    ):
        # Must not raise — outer except catches and updates job state.
        run_grade_pipeline_task(
            job_id="fake-job",
            grade=8,
            langs="en",
            force=False,
            year=2026,
        )

    final_write = json.loads(redis_client.setex.call_args_list[-1].args[2])
    assert final_write["status"] == "failed"
    assert "anthropic 429" in final_write.get("error", "")
