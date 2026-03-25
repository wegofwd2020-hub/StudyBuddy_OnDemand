"""
backend/src/curriculum/schemas.py

Pydantic models for curriculum endpoints.
"""

from __future__ import annotations

from typing import List

from pydantic import BaseModel


class Unit(BaseModel):
    unit_id: str
    title: str
    description: str
    has_lab: bool


class Subject(BaseModel):
    subject_id: str
    name: str
    units: List[Unit]


class GradeCurriculum(BaseModel):
    grade: int
    subjects: List[Subject]


class GradeSummary(BaseModel):
    grade: int
    subject_count: int
    unit_count: int
