"""Put a student on the right side of the lesson-before-quiz gate.

From 2026-09-01 a quiz requires the lesson first (product decision — see
`tests/test_lesson_before_quiz.py`). Tests written before that gate existed open
quiz sessions for students who have never opened anything, which is a state a
real student can no longer be in.

Seeding a lesson view is the honest fix rather than a workaround: these suites
are about quiz mechanics — set rotation, session pinning, phantom sessions — and
their subject is a student who has arrived at the quiz legitimately. The
alternative, exempting tests from the gate, would mean the mechanics were only
ever exercised in a configuration that no longer ships.

Deliberately NOT a conftest autouse fixture: that would satisfy the gate
everywhere, including in the tests whose entire job is to prove it refuses.
"""

from __future__ import annotations

import uuid


async def satisfy_lesson_gate(
    client,
    student_id: str,
    unit_id: str,
    curriculum_id: str,
) -> None:
    """Record that `student_id` has opened `unit_id`'s lesson."""
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO lesson_views (student_id, unit_id, curriculum_id, duration_s)
            VALUES ($1, $2, $3, 60)
            """,
            uuid.UUID(str(student_id)),
            unit_id,
            curriculum_id,
        )
