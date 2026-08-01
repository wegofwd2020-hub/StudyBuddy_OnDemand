"""
Fixture identity for the live quiz suite.

Every id is deterministic (reserved 05000000- block) so a crashed run can always
be cleaned up by re-running teardown. Nothing here is used outside the suite.
"""

from __future__ import annotations

# The suite runs INSIDE the api container, so the app is on localhost.
API_BASE = "http://localhost:8000/api/v1"

CONTENT_ROOT = "/data/content/curricula"
FIXTURE_PATH = "/app/quiz_suite/.fixture.json"

# Must be valid hex UUIDs (0-9a-f only): school_id/student_id are `uuid`
# columns, and asyncpg rejects a non-hex literal client-side before the query
# ever reaches the database. Do not "restore" a mnemonic prefix like 'q'.
SCHOOL_ID = "05000000-0000-0000-0000-000000000001"
STUDENT_A_ID = "05000000-0000-0000-0000-00000000000a"
STUDENT_B_ID = "05000000-0000-0000-0000-00000000000b"

CURRICULUM_ID = "quizsuite-2026-g8"
UNIT_QUIZ = "QS-TEST-001"
UNIT_NOQUIZ = "QS-NOQUIZ-001"
GRADE = 8
YEAR = 2026
SUBJECT = "Science"

# Not *.invalid / *.test / *.localhost: email_validator rejects RFC-2606
# special-use names, and POST /auth/login validates through EmailStr, so a
# fixture on those domains can never log in. quizsuite.example.com is a
# subdomain of the RFC-2606 documentation domain and passes validation.
# Keep the "quizsuite-" local-part prefix on every address — teardown deletes
# exclusively by STUDENT_A_ID/STUDENT_B_ID (see seed.py::_delete_rows), not by
# email, but the prefix is still what keeps the fixture visually
# distinguishable from the 30 real riverside.demo students in the DB.
STUDENT_A_EMAIL = "quizsuite-a@quizsuite.example.com"
STUDENT_B_EMAIL = "quizsuite-b@quizsuite.example.com"
# >= 12 chars, <= 72 bytes (bcrypt limit).
STUDENT_PASSWORD = "QuizSuite-Fixture-2026"
