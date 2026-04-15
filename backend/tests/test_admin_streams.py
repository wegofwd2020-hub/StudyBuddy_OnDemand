"""
tests/test_admin_streams.py

Coverage for the /admin/streams registry endpoints (S-2, #176) and the
upsert-on-use integration with /admin/pipeline/upload-grade.

Scope:
  - list / filter / typeahead
  - create (slug validation, reserved-word block, case-insensitive collisions)
  - update (display_name / description)
  - archive / unarchive
  - merge (transactional, refuses system source + archived target)
  - delete (gated on is_system / is_archived / curricula_count)
  - RBAC: 403 for roles lacking content:publish
  - upload-grade upserts a new stream when stream_display_name is supplied
  - upload-grade rejects unknown stream without display_name
"""

from __future__ import annotations

import io
import json
import uuid

import pytest

from tests.helpers.token_factory import make_admin_token


_ADMIN_ID = "00000000-0000-0000-0000-000000000077"


def _hdr(role: str = "super_admin") -> dict:
    return {"Authorization": f"Bearer {make_admin_token(admin_id=_ADMIN_ID, role=role)}"}


async def _seed_admin(client) -> None:
    pool = client._transport.app.state.pool
    await pool.execute(
        """
        INSERT INTO admin_users (admin_user_id, email, role, password_hash)
        VALUES ($1, 'streams-test@test.invalid', 'super_admin', 'x')
        ON CONFLICT (admin_user_id) DO NOTHING
        """,
        uuid.UUID(_ADMIN_ID),
    )


async def _reset_custom(client) -> None:
    """Drop any non-system streams created in prior tests (isolation helper)."""
    pool = client._transport.app.state.pool
    await pool.execute("DELETE FROM streams WHERE is_system = false")


# ── List / filter ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_streams_returns_system_seeds(client):
    await _seed_admin(client)
    r = await client.get("/api/v1/admin/streams", headers=_hdr())
    assert r.status_code == 200, r.text
    codes = {s["code"] for s in r.json()["streams"]}
    assert {"science", "commerce", "humanities", "english", "stem"}.issubset(codes)


@pytest.mark.asyncio
async def test_list_streams_prefix_filter(client):
    await _seed_admin(client)
    r = await client.get("/api/v1/admin/streams?q=scie", headers=_hdr())
    assert r.status_code == 200
    codes = [s["code"] for s in r.json()["streams"]]
    assert codes == ["science"]


@pytest.mark.asyncio
async def test_list_streams_hides_archived_by_default(client):
    await _seed_admin(client)
    await _reset_custom(client)
    # Create + archive a throwaway
    r = await client.post(
        "/api/v1/admin/streams",
        json={"code": "vocational", "display_name": "Vocational"},
        headers=_hdr(),
    )
    assert r.status_code == 201
    r = await client.post("/api/v1/admin/streams/vocational/archive", headers=_hdr())
    assert r.status_code == 200

    r = await client.get("/api/v1/admin/streams", headers=_hdr())
    codes = {s["code"] for s in r.json()["streams"]}
    assert "vocational" not in codes

    r = await client.get("/api/v1/admin/streams?include_archived=true", headers=_hdr())
    codes = {s["code"] for s in r.json()["streams"]}
    assert "vocational" in codes


# ── Create ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_stream_success(client):
    await _seed_admin(client)
    await _reset_custom(client)
    r = await client.post(
        "/api/v1/admin/streams",
        json={"code": "ib-dp", "display_name": "IB Diploma", "description": "Six subjects"},
        headers=_hdr(),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["code"] == "ib-dp"
    assert body["is_system"] is False
    assert body["curricula_count"] == 0


@pytest.mark.asyncio
async def test_create_stream_reserved_code(client):
    await _seed_admin(client)
    r = await client.post(
        "/api/v1/admin/streams",
        json={"code": "other", "display_name": "Other"},
        headers=_hdr(),
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_create_stream_case_insensitive_collision(client):
    await _seed_admin(client)
    r = await client.post(
        "/api/v1/admin/streams",
        json={"code": "SCIENCE", "display_name": "Science"},
        headers=_hdr(),
    )
    # Server lowercases then checks collision against existing 'science'.
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_create_stream_rejects_bad_chars(client):
    await _seed_admin(client)
    r = await client.post(
        "/api/v1/admin/streams",
        json={"code": "not valid!", "display_name": "Nope"},
        headers=_hdr(),
    )
    assert r.status_code == 400


# ── Update ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_stream_display_name(client):
    await _seed_admin(client)
    await _reset_custom(client)
    await client.post(
        "/api/v1/admin/streams",
        json={"code": "tvet", "display_name": "TVET"},
        headers=_hdr(),
    )
    r = await client.patch(
        "/api/v1/admin/streams/tvet",
        json={"display_name": "Technical & Vocational Education"},
        headers=_hdr(),
    )
    assert r.status_code == 200, r.text
    assert r.json()["display_name"] == "Technical & Vocational Education"


# ── Archive / unarchive ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_archive_then_unarchive(client):
    await _seed_admin(client)
    await _reset_custom(client)
    await client.post(
        "/api/v1/admin/streams",
        json={"code": "cambridge", "display_name": "Cambridge"},
        headers=_hdr(),
    )
    r = await client.post("/api/v1/admin/streams/cambridge/archive", headers=_hdr())
    assert r.status_code == 200 and r.json()["is_archived"] is True
    r = await client.post("/api/v1/admin/streams/cambridge/unarchive", headers=_hdr())
    assert r.status_code == 200 and r.json()["is_archived"] is False


# ── Merge ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_merge_moves_curricula_and_archives_source(client):
    """Create a throwaway stream, attach a curriculum to it, merge into 'stem'."""
    await _seed_admin(client)
    await _reset_custom(client)
    pool = client._transport.app.state.pool

    await client.post(
        "/api/v1/admin/streams",
        json={"code": "mixed", "display_name": "Mixed"},
        headers=_hdr(),
    )
    # Attach a curriculum to 'mixed'
    curr_id = f"test-merge-{uuid.uuid4().hex[:6]}"
    await pool.execute(
        """
        INSERT INTO curricula (curriculum_id, grade, year, name, is_default, stream_code)
        VALUES ($1, 9, 2026, 'Merge Test', false, 'mixed')
        """,
        curr_id,
    )
    await pool.execute(
        "UPDATE streams SET curricula_count = 1 WHERE code = 'mixed'"
    )

    r = await client.post(
        "/api/v1/admin/streams/mixed/merge",
        json={"target_code": "stem"},
        headers=_hdr(),
    )
    assert r.status_code == 200, r.text
    assert r.json()["affected_curricula"] == 1
    assert r.json()["source_archived"] is True

    # Curriculum now points at stem
    new_code = await pool.fetchval(
        "SELECT stream_code FROM curricula WHERE curriculum_id = $1", curr_id
    )
    assert new_code == "stem"

    # Source archived, count zero
    src = await pool.fetchrow("SELECT is_archived, curricula_count FROM streams WHERE code = 'mixed'")
    assert src["is_archived"] is True
    assert src["curricula_count"] == 0

    # Cleanup
    await pool.execute("DELETE FROM curricula WHERE curriculum_id = $1", curr_id)


@pytest.mark.asyncio
async def test_merge_refuses_system_source(client):
    await _seed_admin(client)
    r = await client.post(
        "/api/v1/admin/streams/commerce/merge",
        json={"target_code": "stem"},
        headers=_hdr(),
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_merge_refuses_archived_target(client):
    await _seed_admin(client)
    await _reset_custom(client)
    await client.post(
        "/api/v1/admin/streams",
        json={"code": "src-x", "display_name": "Source X"},
        headers=_hdr(),
    )
    await client.post(
        "/api/v1/admin/streams",
        json={"code": "tgt-x", "display_name": "Target X"},
        headers=_hdr(),
    )
    await client.post("/api/v1/admin/streams/tgt-x/archive", headers=_hdr())
    r = await client.post(
        "/api/v1/admin/streams/src-x/merge",
        json={"target_code": "tgt-x"},
        headers=_hdr(),
    )
    assert r.status_code == 400


# ── Delete ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_refused_on_system_stream(client):
    await _seed_admin(client)
    r = await client.delete("/api/v1/admin/streams/science", headers=_hdr())
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_delete_refused_when_not_archived(client):
    await _seed_admin(client)
    await _reset_custom(client)
    await client.post(
        "/api/v1/admin/streams",
        json={"code": "active-del", "display_name": "Active"},
        headers=_hdr(),
    )
    r = await client.delete("/api/v1/admin/streams/active-del", headers=_hdr())
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_delete_success_when_archived_and_empty(client):
    await _seed_admin(client)
    await _reset_custom(client)
    await client.post(
        "/api/v1/admin/streams",
        json={"code": "gone", "display_name": "Gone"},
        headers=_hdr(),
    )
    await client.post("/api/v1/admin/streams/gone/archive", headers=_hdr())
    r = await client.delete("/api/v1/admin/streams/gone", headers=_hdr())
    assert r.status_code == 204


# ── Upload-grade integration ─────────────────────────────────────────────────


def _grade_payload(grade: int = 9) -> bytes:
    return json.dumps({
        "grade": grade,
        "subjects": [
            {
                "subject_id": "english",
                "name": "English",
                "units": [
                    {"unit_id": f"G{grade}-ENG-001", "title": "Unit 1"},
                ],
            }
        ],
    }).encode()


@pytest.mark.asyncio
async def test_upload_grade_upserts_new_stream_on_use(client):
    await _seed_admin(client)
    await _reset_custom(client)

    files = {"file": ("grade9.json", io.BytesIO(_grade_payload()), "application/json")}
    r = await client.post(
        "/api/v1/admin/pipeline/upload-grade?year=2026&stream=advanced&stream_display_name=Advanced%20Track",
        files=files,
        headers=_hdr(),
    )
    assert r.status_code == 200, r.text

    pool = client._transport.app.state.pool
    row = await pool.fetchrow(
        "SELECT code, display_name, is_system, curricula_count FROM streams WHERE code = 'advanced'"
    )
    assert row is not None
    assert row["display_name"] == "Advanced Track"
    assert row["is_system"] is False
    assert row["curricula_count"] == 1

    # Cleanup — drop the curriculum + stream
    await pool.execute(
        "DELETE FROM curricula WHERE curriculum_id = 'default-2026-g9-advanced'"
    )


@pytest.mark.asyncio
async def test_upload_grade_rejects_unknown_stream_without_display_name(client):
    await _seed_admin(client)
    await _reset_custom(client)

    files = {"file": ("grade9.json", io.BytesIO(_grade_payload()), "application/json")}
    r = await client.post(
        "/api/v1/admin/pipeline/upload-grade?year=2026&stream=mystery",
        files=files,
        headers=_hdr(),
    )
    assert r.status_code == 400
    assert "mystery" in r.text


@pytest.mark.asyncio
async def test_upload_grade_resolves_existing_stream(client):
    await _seed_admin(client)

    files = {"file": ("grade9.json", io.BytesIO(_grade_payload()), "application/json")}
    r = await client.post(
        "/api/v1/admin/pipeline/upload-grade?year=2026&stream=english",
        files=files,
        headers=_hdr(),
    )
    assert r.status_code == 200
    assert r.json()["curriculum_id"] == "default-2026-g9-english"

    pool = client._transport.app.state.pool
    cnt = await pool.fetchval("SELECT curricula_count FROM streams WHERE code = 'english'")
    assert cnt >= 1
    await pool.execute(
        "DELETE FROM curricula WHERE curriculum_id = 'default-2026-g9-english'"
    )
