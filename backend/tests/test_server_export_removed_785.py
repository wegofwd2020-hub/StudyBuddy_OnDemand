"""
tests/test_server_export_removed_785.py

The server-side CSV export is gone, and stays gone (#785).

`POST /reports/school/{id}/export` accepted six `report_type` values, logged
the one it was given, and always wrote the same file: enrolled students with a
progress summary. Its own comment called it a "Minimal export". Nothing in the
product called it — the Export page builds every CSV in the browser from the
report endpoints, with each report's own columns and filters — so the only way
to reach the stub was a direct API call.

It was also the one report path that returned a FILE of student records, and it
had already needed two security fixes (#784): no grade scoping, so a Grade 5
teacher could download the whole school's roster; and a download route with no
ownership check. Finishing it would have duplicated what the browser export
already does, on a surface that had proved easy to get wrong. Decision
(2026-09-16): remove it.

If a server-side export is ever needed again — a report too large to build in a
browser — it should be designed from the report it exports, not revived from
this stub. These tests exist so it is not revived by accident.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from tests.helpers.token_factory import make_teacher_token


def _admin_headers(school_id: str) -> dict:
    token = make_teacher_token(school_id=school_id, role="school_admin")
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_the_export_endpoint_no_longer_exists(client: AsyncClient, db_conn):
    school_id = str(uuid.uuid4())
    r = await client.post(
        f"/api/v1/reports/school/{school_id}/export",
        json={"report_type": "feedback", "filters": {}},
        headers=_admin_headers(school_id),
    )
    assert r.status_code in (404, 405), r.text


@pytest.mark.asyncio
async def test_the_download_endpoint_no_longer_exists(client: AsyncClient, db_conn):
    school_id = str(uuid.uuid4())
    r = await client.get(
        f"/api/v1/reports/download/{uuid.uuid4()}",
        headers=_admin_headers(school_id),
    )
    assert r.status_code == 404, r.text
    # A random id 404'd while the handler existed too ("export_not_found"), so
    # the status alone proves nothing. The ROUTE must be gone, not the file.
    assert "export_not_found" not in r.text, r.text


def test_the_export_task_is_not_registered():
    import src.auth.tasks  # noqa: F401 — registers every task on the app
    from src.core.celery_app import celery_app

    assert "src.auth.tasks.export_report_task" not in celery_app.tasks
    assert "src.auth.tasks.export_report_task" not in (celery_app.conf.task_routes or {})
