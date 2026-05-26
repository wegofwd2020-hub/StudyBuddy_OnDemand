"""
Endpoint + service tests for the Curriculum Authoring Studio — PR-B
(generate → review → regenerate-with-reason → snapshot/restore → publish).
"""

from __future__ import annotations

import json
import os
import sys
from unittest.mock import patch

import pytest
from httpx import AsyncClient
from main import app

from src.admin import authoring_generation as gen
from src.admin import authoring_service as svc

# run_analysis / generation lazily import the `pipeline` package (repo root).
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


# ── A fake provider that answers every authoring prompt type ──────────────────


def _valid_lesson() -> dict:
    return {
        "unit_id": "U", "subject": "Physics", "topic": "Motion",
        "synopsis": "A short but valid synopsis of the lesson.",
        "sections": [
            {"heading": "Introduction", "body": "Intro body with a diagram.\n\n"
             "```mermaid\ngraph TD; A-->B;\n```"},
            {"heading": "Core Concepts", "body": "Core concepts body text here."},
        ],
        "key_points": ["kp one", "kp two"],
        "learning_objectives": ["Explain motion", "Calculate speed"],
        "reading_level": "Grade 9", "estimated_duration_minutes": 40,
        "language": "en", "generated_at": "2026-01-01T00:00:00Z",
        "model": "fake-model", "content_version": 1,
    }


def _valid_quiz(set_number: int = 1) -> dict:
    q = {
        "question_id": "q1", "question_text": "What is speed?",
        "question_type": "multiple_choice",
        "options": [
            {"option_id": "A", "text": "distance/time"},
            {"option_id": "B", "text": "time/distance"},
            {"option_id": "C", "text": "mass"},
            {"option_id": "D", "text": "force"},
        ],
        "correct_option": "A", "explanation": "Speed is distance over time.",
        "difficulty": "easy",
    }
    return {
        "unit_id": "U", "set_number": set_number, "language": "en",
        "questions": [{**q, "question_id": f"q{i + 1}"} for i in range(8)],
        "total_questions": 8, "estimated_duration_minutes": 10, "passing_score": 6,
        "generated_at": "2026-01-01T00:00:00Z", "model": "fake-model", "content_version": 1,
    }


def _valid_tutorial() -> dict:
    return {
        "unit_id": "U", "language": "en", "title": "Motion tutorial",
        "sections": [{
            "section_id": "s1", "title": "Step 1",
            "content": "Section content that is long enough.",
            "examples": ["example one"], "practice_question": "Try this problem.",
        }],
        "common_mistakes": ["mixing up speed and velocity"],
        "generated_at": "2026-01-01T00:00:00Z", "model": "fake-model", "content_version": 1,
    }


class _FakeProvider:
    """Answers structurer / flow / lesson / quiz / tutorial prompts."""

    model = "fake-model"

    def generate(self, prompt: str) -> tuple[str, int, int]:
        if "pedagogy reviewer" in prompt:
            return json.dumps({"summary": "ok", "warnings": []}), 10, 10
        if "curriculum architect" in prompt:
            return json.dumps({"subjects": [{"subject_label": "Physics", "units": [
                {"title": "Motion", "subtopics": ["Speed"], "prerequisites": []}]}]}), 10, 10
        if "creating a quiz" in prompt:
            set_number = 1
            for n in (1, 2, 3):
                if f"set {n} of" in prompt:
                    set_number = n
            return json.dumps(_valid_quiz(set_number)), 10, 10
        if "worked tutorial" in prompt:
            return json.dumps(_valid_tutorial()), 10, 10
        return json.dumps(_valid_lesson()), 10, 10


async def _seed_generated_project(*, units: int = 1) -> str:
    """Create → analyze → materialize → generate, committed on the app pool."""
    subjects = [{
        "subject_label": "Physics",
        "units": [
            {"title": f"Topic {i + 1}", "subtopics": ["a"], "prerequisites": []}
            for i in range(units)
        ],
    }]
    async with app.state.pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        project = await svc.create_project(
            conn, title="G9 Physics", grade=9, languages=["en"],
            raw_toc="1. Motion", created_by=None,
        )
        pid = project["project_id"]
        # Set the structured TOC directly (skip the analyze round-trip).
        await conn.execute(
            "UPDATE authoring_projects SET structured_toc=$2, status='analyzed' WHERE project_id=$1",
            pid, {"subjects": subjects},
        )
        await svc.materialize(conn, pid, None)
        await gen.generate_topics(conn, pid, langs=["en"], provider=_FakeProvider())
    return pid


def _first_unit_id(pid: str) -> str:
    # Deterministic from materialize: AUTH-{proj8}-PHYSIC-001
    return f"AUTH-{pid.replace('-', '')[:8]}-PHYSIC-001"


# ── Generate ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_generate_topics_service_creates_active_versions(client: AsyncClient) -> None:
    pid = await _seed_generated_project()
    async with app.state.pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        status = await conn.fetchval(
            "SELECT status FROM authoring_projects WHERE project_id=$1", pid
        )
        n_active = await conn.fetchval(
            "SELECT COUNT(*) FROM authoring_active_versions WHERE project_id=$1", pid
        )
    assert status == "generated"
    assert n_active == 5  # lesson + tutorial + 3 quiz sets


@pytest.mark.asyncio
async def test_generate_endpoint_dispatches(client: AsyncClient, admin_token: str) -> None:
    pid = await _seed_generated_project()
    with patch("src.core.celery_app.celery_app.send_task") as send_task:
        r = await client.post(
            f"/api/v1/admin/authoring/projects/{pid}/generate",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"langs": "en", "force": True},
        )
    assert r.status_code == 202
    assert r.json()["status"] == "generating"
    send_task.assert_called_once()


@pytest.mark.asyncio
async def test_generate_requires_materialized(client: AsyncClient, admin_token: str) -> None:
    headers = {"Authorization": f"Bearer {admin_token}"}
    created = await client.post(
        "/api/v1/admin/authoring/projects", headers=headers,
        json={"title": "X", "grade": 9, "languages": ["en"], "raw_toc": "1. A"},
    )
    pid = created.json()["project_id"]
    r = await client.post(
        f"/api/v1/admin/authoring/projects/{pid}/generate", headers=headers, json={}
    )
    assert r.status_code == 409


# ── View / regenerate / accept ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_view_topic_returns_active(client: AsyncClient, admin_token: str) -> None:
    pid = await _seed_generated_project()
    unit_id = _first_unit_id(pid)
    r = await client.get(
        f"/api/v1/admin/authoring/projects/{pid}/topics/{unit_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        params={"content_type": "lesson"},
    )
    assert r.status_code == 200
    assert r.json()["version_number"] == 1
    assert r.json()["body"]["sections"]


@pytest.mark.asyncio
async def test_regenerate_is_append_only_unlimited_with_flow_recheck(
    client: AsyncClient, admin_token: str
) -> None:
    pid = await _seed_generated_project()
    unit_id = _first_unit_id(pid)
    headers = {"Authorization": f"Bearer {admin_token}"}

    with patch.object(gen, "_build_authoring_provider", return_value=_FakeProvider()):
        for i in range(3):  # unlimited
            r = await client.post(
                f"/api/v1/admin/authoring/projects/{pid}/topics/{unit_id}/regenerate",
                headers=headers,
                json={"content_type": "lesson", "reason": f"too terse, expand ({i})"},
            )
            assert r.status_code == 200
            assert "flow_recheck" in r.json()

    hist = await client.get(
        f"/api/v1/admin/authoring/projects/{pid}/topics/{unit_id}",
        headers=headers, params={"content_type": "lesson", "history": 1},
    )
    versions = hist.json()["versions"]
    assert [v["version_number"] for v in versions] == [4, 3, 2, 1]
    assert versions[0]["is_active"] is True
    assert versions[0]["regen_reason"].startswith("too terse")


@pytest.mark.asyncio
async def test_regenerate_requires_reason(client: AsyncClient, admin_token: str) -> None:
    pid = await _seed_generated_project()
    unit_id = _first_unit_id(pid)
    r = await client.post(
        f"/api/v1/admin/authoring/projects/{pid}/topics/{unit_id}/regenerate",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"content_type": "lesson", "reason": ""},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_accept_topic(client: AsyncClient, admin_token: str) -> None:
    pid = await _seed_generated_project()
    unit_id = _first_unit_id(pid)
    r = await client.post(
        f"/api/v1/admin/authoring/projects/{pid}/topics/{unit_id}/accept",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"content_type": "lesson"},
    )
    assert r.status_code == 200
    assert r.json()["review_status"] == "accepted"


# ── Snapshot / restore ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_snapshot_and_restore_round_trip(client: AsyncClient, admin_token: str) -> None:
    pid = await _seed_generated_project()
    unit_id = _first_unit_id(pid)
    headers = {"Authorization": f"Bearer {admin_token}"}

    snap = await client.post(
        f"/api/v1/admin/authoring/projects/{pid}/snapshots",
        headers=headers, json={"label": "before edits"},
    )
    assert snap.status_code == 201
    snapshot_id = snap.json()["snapshot_id"]

    # Mutate the lesson topic (new active version 2).
    with patch.object(gen, "_build_authoring_provider", return_value=_FakeProvider()):
        await client.post(
            f"/api/v1/admin/authoring/projects/{pid}/topics/{unit_id}/regenerate",
            headers=headers, json={"content_type": "lesson", "reason": "rewrite"},
        )
    mutated = await client.get(
        f"/api/v1/admin/authoring/projects/{pid}/topics/{unit_id}",
        headers=headers, params={"content_type": "lesson"},
    )
    assert mutated.json()["version_number"] == 2

    # Restore → active lesson back to version 1.
    rest = await client.post(
        f"/api/v1/admin/authoring/projects/{pid}/snapshots/{snapshot_id}/restore",
        headers=headers,
    )
    assert rest.status_code == 200
    after = await client.get(
        f"/api/v1/admin/authoring/projects/{pid}/topics/{unit_id}",
        headers=headers, params={"content_type": "lesson"},
    )
    assert after.json()["version_number"] == 1


# ── Publish ──────────────────────────────────────────────────────────────────


async def _accept_all(pid: str) -> None:
    async with app.state.pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            UPDATE authoring_topic_versions tv SET review_status='accepted'
              FROM authoring_active_versions av
             WHERE av.topic_version_id = tv.topic_version_id AND av.project_id = $1
            """,
            pid,
        )


@pytest.mark.asyncio
async def test_publish_requires_all_accepted(client: AsyncClient, admin_token: str) -> None:
    pid = await _seed_generated_project()
    r = await client.post(
        f"/api/v1/admin/authoring/projects/{pid}/publish",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"visibility": "private"},
    )
    assert r.status_code == 409  # topics still pending


@pytest.mark.asyncio
async def test_publish_catalog_sets_is_default(
    client: AsyncClient, admin_token: str
) -> None:
    pid = await _seed_generated_project()
    await _accept_all(pid)
    r = await client.post(
        f"/api/v1/admin/authoring/projects/{pid}/publish",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"visibility": "catalog"},
    )
    assert r.status_code == 200
    curriculum_id = r.json()["curriculum_id"]
    assert r.json()["files_written"] == 5

    async with app.state.pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        is_default = await conn.fetchval(
            "SELECT is_default FROM curricula WHERE curriculum_id=$1", curriculum_id
        )
        status = await conn.fetchval(
            "SELECT status FROM authoring_projects WHERE project_id=$1", pid
        )
        csv_count = await conn.fetchval(
            "SELECT COUNT(*) FROM content_subject_versions WHERE curriculum_id=$1", curriculum_id
        )
    assert is_default is True
    assert status == "published"
    assert csv_count >= 1


@pytest.mark.asyncio
async def test_publish_private_keeps_is_default_false(
    client: AsyncClient, admin_token: str
) -> None:
    pid = await _seed_generated_project()
    await _accept_all(pid)
    r = await client.post(
        f"/api/v1/admin/authoring/projects/{pid}/publish",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"visibility": "private"},
    )
    assert r.status_code == 200
    async with app.state.pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        is_default = await conn.fetchval(
            "SELECT is_default FROM curricula WHERE curriculum_id=$1", r.json()["curriculum_id"]
        )
    assert is_default is False
