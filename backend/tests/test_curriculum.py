"""
tests/test_curriculum.py

Tests for curriculum endpoints.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_curriculum_returns_all_grades(client: AsyncClient):
    """GET /curriculum returns a list of all available grades (5–12)."""
    response = await client.get("/api/v1/curriculum")
    assert response.status_code == 200, response.text
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 8  # grades 5 through 12
    grades = [item["grade"] for item in data]
    assert sorted(grades) == list(range(5, 13))


@pytest.mark.asyncio
async def test_list_curriculum_has_counts(client: AsyncClient):
    """Each grade summary includes subject_count and unit_count."""
    response = await client.get("/api/v1/curriculum")
    assert response.status_code == 200
    for item in response.json():
        assert "grade" in item
        assert "subject_count" in item
        assert "unit_count" in item
        assert item["subject_count"] >= 4
        assert item["unit_count"] >= 16


@pytest.mark.asyncio
async def test_get_grade_8_curriculum(client: AsyncClient):
    """GET /curriculum/8 returns full grade 8 subjects and units."""
    response = await client.get("/api/v1/curriculum/8")
    assert response.status_code == 200
    data = response.json()
    assert data["grade"] == 8
    assert isinstance(data["subjects"], list)
    assert len(data["subjects"]) >= 4

    for subject in data["subjects"]:
        assert "subject_id" in subject
        assert "name" in subject
        assert isinstance(subject["units"], list)
        assert len(subject["units"]) >= 4

        for unit in subject["units"]:
            assert "unit_id" in unit
            assert "title" in unit
            assert "description" in unit
            assert "has_lab" in unit


@pytest.mark.asyncio
async def test_get_grade_5_curriculum(client: AsyncClient):
    """GET /curriculum/5 returns grade 5 data."""
    response = await client.get("/api/v1/curriculum/5")
    assert response.status_code == 200
    assert response.json()["grade"] == 5


@pytest.mark.asyncio
async def test_get_grade_12_curriculum(client: AsyncClient):
    """GET /curriculum/12 returns grade 12 data."""
    response = await client.get("/api/v1/curriculum/12")
    assert response.status_code == 200
    assert response.json()["grade"] == 12


@pytest.mark.asyncio
async def test_get_invalid_grade_too_low(client: AsyncClient):
    """GET /curriculum/4 returns 400 (grade out of range)."""
    response = await client.get("/api/v1/curriculum/4")
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_invalid_grade_too_high(client: AsyncClient):
    """GET /curriculum/13 returns 400 (grade out of range)."""
    response = await client.get("/api/v1/curriculum/13")
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_curriculum_has_lab_units(client: AsyncClient):
    """Some science units should have has_lab=True."""
    found_lab = False
    for grade in range(5, 13):
        response = await client.get(f"/api/v1/curriculum/{grade}")
        for subject in response.json()["subjects"]:
            for unit in subject["units"]:
                if unit.get("has_lab"):
                    found_lab = True
                    break
    assert found_lab, "Expected at least one unit with has_lab=True across all grades"


@pytest.mark.asyncio
async def test_curriculum_l1_cache(client: AsyncClient):
    """Second request for same grade returns cached data (no error)."""
    r1 = await client.get("/api/v1/curriculum/8")
    r2 = await client.get("/api/v1/curriculum/8")
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json() == r2.json()
