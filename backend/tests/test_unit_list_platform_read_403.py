"""
tests/test_unit_list_platform_read_403.py

The unit-status list (GET /schools/{id}/content/{curriculum_id}/units) is a read.
A school may read a platform curriculum that one of its classrooms holds, before
it has forked it. It may not read a platform curriculum no classroom of its holds,
nor another school's fork. Writes against a platform curriculum stay owner-only.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from tests.test_quiz_override_grading_804 import (  # noqa: F401 - fixtures
    _OOB_CURRICULUM_ID,
    _UNIT_ID,
    _adopt_and_import,
    _register,
    oob_curriculum,
    quiz_content_store,
)


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _hold_platform_curriculum(client: AsyncClient, school_id: str) -> None:
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        classroom_id = await conn.fetchval(
            "INSERT INTO classrooms (school_id, name, grade) VALUES ($1, $2, $3)"
            " RETURNING classroom_id",
            uuid.UUID(school_id),
            f"Read Room {school_id[:6]}",
            8,
        )
        await conn.execute(
            "INSERT INTO classroom_packages (classroom_id, curriculum_id) VALUES ($1, $2)",
            classroom_id,
            _OOB_CURRICULUM_ID,
        )


@pytest.mark.asyncio
async def test_platform_curriculum_no_classroom_holds_is_403(
    client: AsyncClient, db_conn, oob_curriculum, quiz_content_store
) -> None:
    school = await _register(client, "Unserved Read 403", "unserved-read-403@example.com")

    r = await client.get(
        f"/api/v1/schools/{school['school_id']}/content/{_OOB_CURRICULUM_ID}/units",
        headers=_auth(school["access_token"]),
    )

    assert r.status_code == 403, r.text


@pytest.mark.asyncio
async def test_platform_curriculum_a_classroom_holds_is_readable_before_forking(
    client: AsyncClient, db_conn, oob_curriculum, quiz_content_store
) -> None:
    school = await _register(client, "Served Read 403", "served-read-403@example.com")
    await _hold_platform_curriculum(client, school["school_id"])

    r = await client.get(
        f"/api/v1/schools/{school['school_id']}/content/{_OOB_CURRICULUM_ID}/units",
        headers=_auth(school["access_token"]),
    )

    assert r.status_code == 200, r.text
    assert _UNIT_ID in r.text


@pytest.mark.asyncio
async def test_another_schools_fork_is_403(
    client: AsyncClient, db_conn, oob_curriculum, quiz_content_store
) -> None:
    owner = await _register(client, "Fork Owner 403", "fork-owner-403@example.com")
    fork_id = await _adopt_and_import(client, owner["school_id"], owner["access_token"])
    peer = await _register(client, "Fork Peer 403", "fork-peer-403@example.com")

    r = await client.get(
        f"/api/v1/schools/{peer['school_id']}/content/{fork_id}/units",
        headers=_auth(peer["access_token"]),
    )

    assert r.status_code == 403, r.text


@pytest.mark.asyncio
async def test_a_schools_own_fork_is_still_readable(
    client: AsyncClient, db_conn, oob_curriculum, quiz_content_store
) -> None:
    owner = await _register(client, "Own Fork 403", "own-fork-403@example.com")
    fork_id = await _adopt_and_import(client, owner["school_id"], owner["access_token"])

    r = await client.get(
        f"/api/v1/schools/{owner['school_id']}/content/{fork_id}/units",
        headers=_auth(owner["access_token"]),
    )

    assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_writes_to_a_served_platform_curriculum_stay_403(
    client: AsyncClient, db_conn, oob_curriculum, quiz_content_store
) -> None:
    school = await _register(client, "Write Read 403", "write-read-403@example.com")
    await _hold_platform_curriculum(client, school["school_id"])

    r = await client.post(
        f"/api/v1/schools/{school['school_id']}/content/{_OOB_CURRICULUM_ID}"
        f"/units/{_UNIT_ID}/review",
        json={"lang": "en"},
        headers=_auth(school["access_token"]),
    )

    assert r.status_code == 403, r.text
