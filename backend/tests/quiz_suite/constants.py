"""
Fixture identity for the live quiz suite.

Every id is deterministic (reserved q5000000- block) so a crashed run can always
be cleaned up by re-running teardown. Nothing here is used outside the suite.
"""

from __future__ import annotations

# The suite runs INSIDE the api container, so the app is on localhost.
API_BASE = "http://localhost:8000/api/v1"

CONTENT_ROOT = "/data/content/curricula"
FIXTURE_PATH = "/app/tests/quiz_suite/.fixture.json"

SCHOOL_ID = "q5000000-0000-0000-0000-000000000001"
STUDENT_A_ID = "q5000000-0000-0000-0000-00000000000a"
STUDENT_B_ID = "q5000000-0000-0000-0000-00000000000b"

CURRICULUM_ID = "quizsuite-2026-g8"
UNIT_QUIZ = "QS-TEST-001"
UNIT_NOQUIZ = "QS-NOQUIZ-001"
GRADE = 8
YEAR = 2026
SUBJECT = "Science"

STUDENT_A_EMAIL = "quizsuite-a@test.invalid"
STUDENT_B_EMAIL = "quizsuite-b@test.invalid"
# >= 12 chars, <= 72 bytes (bcrypt limit).
STUDENT_PASSWORD = "QuizSuite-Fixture-2026"
