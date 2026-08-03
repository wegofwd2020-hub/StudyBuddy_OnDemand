"""The fixture must produce a student who can actually log in and see content."""

from __future__ import annotations

import pytest

from quiz_suite import constants as C

pytestmark = pytest.mark.quiz_live


@pytest.mark.asyncio
async def test_seeded_student_can_log_in(auth_a):
    assert auth_a["Authorization"].startswith("Bearer ey")


@pytest.mark.asyncio
async def test_seeded_unit_serves_a_quiz(api, auth_a):
    r = await api.get(f"/content/{C.UNIT_QUIZ}/quiz", headers=auth_a)
    assert r.status_code == 200, r.text
    assert len(r.json()["questions"]) == 3


@pytest.mark.asyncio
async def test_seeded_quiz_unit_serves_a_lesson(api, auth_a):
    # LessonResponse requires grade/subject/lang beyond unit_id/title/sections/
    # key_points; _normalize_lesson() passes a dict containing "title" straight
    # through with no enrichment, so a fixture missing any of those 500s.
    r = await api.get(f"/content/{C.UNIT_QUIZ}/lesson", headers=auth_a)
    assert r.status_code == 200, r.text
    assert r.json()["title"]


@pytest.mark.asyncio
async def test_seeded_noquiz_unit_serves_a_lesson(api, auth_a):
    # UNIT_NOQUIZ has a lesson but deliberately no quiz files.
    r = await api.get(f"/content/{C.UNIT_NOQUIZ}/lesson", headers=auth_a)
    assert r.status_code == 200, r.text
    assert r.json()["title"]


@pytest.mark.asyncio
async def test_fixture_file_records_the_answer_key(fixture_data):
    assert set(fixture_data["answer_key"]) == {"1", "2", "3"}
    # q1 is correct option "B", which sits at index 0 — the alphabetical trap.
    assert fixture_data["answer_key"]["1"]["q1"] == 0
