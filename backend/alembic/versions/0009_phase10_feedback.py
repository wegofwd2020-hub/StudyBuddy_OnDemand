"""
backend/alembic/versions/0009_phase10_feedback.py

Phase 10 schema additions:
  feedback — student product feedback (content quality, UX, general)
             Separate from student_content_feedback (content moderation flags).
"""

revision = "0009"
down_revision = "0008"

from alembic import op


def upgrade() -> None:
    # ── feedback ──────────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            feedback_id     uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
            student_id      uuid        NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
            category        text        NOT NULL
                            CHECK (category IN ('content', 'ux', 'general')),
            unit_id         text,
            curriculum_id   text,
            message         text        NOT NULL,
            rating          smallint    CHECK (rating IS NULL OR rating BETWEEN 1 AND 5),
            submitted_at    timestamptz NOT NULL DEFAULT NOW(),
            reviewed        boolean     NOT NULL DEFAULT false,
            reviewed_by     uuid        REFERENCES admin_users(admin_user_id) ON DELETE SET NULL,
            reviewed_at     timestamptz
        )
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_feedback_student
        ON feedback(student_id, submitted_at DESC)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_feedback_category_reviewed
        ON feedback(category, reviewed)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_feedback_submitted
        ON feedback(submitted_at DESC)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_feedback_submitted")
    op.execute("DROP INDEX IF EXISTS ix_feedback_category_reviewed")
    op.execute("DROP INDEX IF EXISTS ix_feedback_student")
    op.execute("DROP TABLE IF EXISTS feedback CASCADE")
