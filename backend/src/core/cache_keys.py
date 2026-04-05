"""
backend/src/core/cache_keys.py

Central Redis key builders (ADR-001 Decision 3 — Redis key namespacing).

Key convention
--------------
School-scoped data is prefixed with `school:{school_id}:` so that:
  1. A SCAN school:{school_id}:* immediately yields all cached data for one school.
  2. Bulk invalidation on subscription change, school transfer, or curriculum
     activation requires no DB lookup — just delete by prefix.
  3. Key collisions between platform and school data are structurally impossible.

Keys for students NOT enrolled in a school (demo students, unaffiliated) use
the unscoped forms — those students use the platform-default curriculum and
have no school subscription, so school namespacing is meaningless for them.

Exported key builders
---------------------
  ent_key(student_id, school_id)        — student entitlement cache
  cur_key(student_id, school_id)        — curriculum resolver cache
  school_ent_key(school_id)             — school-level entitlement derived cache
  school_scan_pattern(school_id)        — SCAN pattern for bulk school eviction

Platform-only keys (not school-scoped)
  content_key(curriculum_id, unit_id, filename)
  csv_key(curriculum_id, subject)
  quiz_set_key(student_id, unit_id)

  suspended:{id}             — suspension flag  (platform-wide, not school data)
  demo_blacklist:{jti}       — demo student token blacklist
  demo_teacher_blacklist:{jti} — demo teacher token blacklist
  rate_limit:*               — rate limit counters
  admin_reset:*              — admin password reset tokens
"""

from __future__ import annotations


# ── School-scoped keys ────────────────────────────────────────────────────────


def ent_key(student_id: str, school_id: str | None) -> str:
    """
    Redis key for a student's entitlement cache.

    school:{school_id}:ent:{student_id}  — school-enrolled student
    ent:{student_id}                     — unaffiliated / demo student
    """
    if school_id:
        return f"school:{school_id}:ent:{student_id}"
    return f"ent:{student_id}"


def cur_key(student_id: str, school_id: str | None) -> str:
    """
    Redis key for the curriculum resolver result for a student.

    school:{school_id}:cur:{student_id}  — school-enrolled student
    cur:{student_id}                     — unaffiliated / demo student
    """
    if school_id:
        return f"school:{school_id}:cur:{student_id}"
    return f"cur:{student_id}"


def school_ent_key(school_id: str) -> str:
    """
    Redis key for the school-level derived entitlement blob.

    school:{school_id}:ent
    (was: ent:school:{school_id})
    """
    return f"school:{school_id}:ent"


def school_scan_pattern(school_id: str) -> str:
    """
    SCAN match pattern that matches ALL cached data for a school.

    Use this for bulk eviction on subscription change / school transfer /
    curriculum activation — no need to enumerate enrolled student IDs.
    """
    return f"school:{school_id}:*"


# ── Platform / content keys (not school-scoped) ───────────────────────────────


def content_key(curriculum_id: str, unit_id: str, filename: str) -> str:
    """content:{curriculum_id}:{unit_id}:{filename}"""
    return f"content:{curriculum_id}:{unit_id}:{filename}"


def csv_key(curriculum_id: str, subject: str) -> str:
    """csv:{curriculum_id}:{subject}"""
    return f"csv:{curriculum_id}:{subject}"


def quiz_set_key(student_id: str, unit_id: str) -> str:
    """quiz_set:{student_id}:{unit_id}"""
    return f"quiz_set:{student_id}:{unit_id}"
