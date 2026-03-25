"""
backend/src/curriculum/router.py

Curriculum endpoints — serve grade metadata from data/*.json files.

Routes:
  GET /curriculum          — list of grades with subject/unit counts
  GET /curriculum/{grade}  — full grade tree (subjects + units)

The grade data is cached in L1 TTLCache (1-hr TTL).
These endpoints do not require authentication (curriculum listing is public).

Prefixed with /api/v1 in main.py.
"""

from __future__ import annotations

import json
import os
from typing import List

from fastapi import APIRouter, HTTPException, Request

from src.core.cache import curriculum_cache
from src.curriculum.schemas import GradeCurriculum, GradeSummary
from src.utils.logger import get_logger

log = get_logger("curriculum")
router = APIRouter(tags=["curriculum"])

# Path to data directory (relative to repo root, resolved at import time).
_DATA_DIR = os.path.join(
    os.path.dirname(__file__),   # backend/src/curriculum/
    "..", "..", "..",             # → repo root
    "data",
)
_DATA_DIR = os.path.abspath(_DATA_DIR)


def _load_grade(grade: int) -> dict:
    """
    Load grade data from L1 cache, falling back to the JSON file.

    Raises HTTPException 404 if the grade file does not exist.
    """
    cached = curriculum_cache.get(grade)
    if cached is not None:
        return cached

    path = os.path.join(_DATA_DIR, f"grade{grade}_stem.json")
    if not os.path.exists(path):
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "detail": f"Curriculum data for grade {grade} not found."},
        )

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    curriculum_cache[grade] = data
    log.info("curriculum_loaded", grade=grade)
    return data


@router.get("/curriculum", response_model=List[GradeSummary])
async def list_curriculum(request: Request):
    """
    Return a summary list of all available grades.

    Response shape:
      [{"grade": 5, "subject_count": 4, "unit_count": 24}, ...]
    """
    summaries: List[GradeSummary] = []

    for grade in range(5, 13):
        try:
            data = _load_grade(grade)
        except HTTPException:
            continue

        subjects = data.get("subjects", [])
        unit_count = sum(len(s.get("units", [])) for s in subjects)
        summaries.append(
            GradeSummary(
                grade=grade,
                subject_count=len(subjects),
                unit_count=unit_count,
            )
        )

    return summaries


@router.get("/curriculum/{grade}", response_model=GradeCurriculum)
async def get_grade_curriculum(grade: int, request: Request):
    """Return the full subject + unit tree for a grade (5–12)."""
    cid = getattr(request.state, "correlation_id", "")

    if not (5 <= grade <= 12):
        raise HTTPException(
            status_code=400,
            detail={"error": "bad_request", "detail": "Grade must be between 5 and 12.", "correlation_id": cid},
        )

    data = _load_grade(grade)
    return GradeCurriculum(**data)
