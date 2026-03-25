"""phase3_progress_schema

Revision ID: 0003
Revises: 0002
Create Date: 2026-03-25

Phase 3 schema: progress tracking tables and materialized view.

Tables created:
  progress_sessions             — one row per quiz attempt (open or closed)
  progress_answers              — individual question answers within a session
  lesson_views                  — lesson open/close lifecycle events

Materialized view:
  mv_student_curriculum_progress — per (student_id × unit_id) roll-up; unit status badges
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── progress_sessions ────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS progress_sessions (
            session_id      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            student_id      UUID        NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
            unit_id         TEXT        NOT NULL,
            curriculum_id   TEXT        NOT NULL,
            grade           SMALLINT    NOT NULL,
            subject         TEXT        NOT NULL,
            started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            ended_at        TIMESTAMPTZ,
            score           SMALLINT,
            total_questions SMALLINT,
            completed       BOOLEAN     NOT NULL DEFAULT FALSE,
            attempt_number  SMALLINT    NOT NULL DEFAULT 1,
            passed          BOOLEAN
        )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS idx_sessions_student ON progress_sessions(student_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_sessions_unit    ON progress_sessions(unit_id, curriculum_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_sessions_ended   ON progress_sessions(student_id, ended_at DESC NULLS LAST)")

    # ── progress_answers ─────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS progress_answers (
            answer_id      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            session_id     UUID        NOT NULL REFERENCES progress_sessions(session_id) ON DELETE CASCADE,
            event_id       TEXT        UNIQUE,        -- mobile offline deduplication key
            question_id    TEXT        NOT NULL,
            student_answer SMALLINT,
            correct_answer SMALLINT,
            correct        BOOLEAN,
            ms_taken       INT,
            recorded_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS idx_answers_session ON progress_answers(session_id)")

    # ── lesson_views ──────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS lesson_views (
            view_id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            student_id        UUID        NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
            unit_id           TEXT        NOT NULL,
            curriculum_id     TEXT        NOT NULL,
            duration_s        INT,
            audio_played      BOOLEAN     NOT NULL DEFAULT FALSE,
            experiment_viewed BOOLEAN     NOT NULL DEFAULT FALSE,
            started_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            ended_at          TIMESTAMPTZ
        )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS idx_views_student      ON lesson_views(student_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_views_student_date ON lesson_views(student_id, started_at)")

    # ── mv_student_curriculum_progress ───────────────────────────────────────
    # Status logic:
    #   completed   — at least one passed closed session
    #   needs_retry — closed sessions exist but none passed
    #   in_progress — open (incomplete) session exists
    #   not_started — no sessions
    op.execute("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS mv_student_curriculum_progress AS
        SELECT
            s.student_id,
            s.unit_id,
            s.curriculum_id,
            s.subject,
            s.grade,
            COUNT(s.session_id)                                   AS attempts,
            MAX(s.score)                                          AS best_score,
            MAX(s.score::float / NULLIF(s.total_questions, 0) * 100) AS best_pct,
            CASE
                WHEN MAX(CASE WHEN s.passed AND s.completed THEN 1 ELSE 0 END) = 1 THEN 'completed'
                WHEN MAX(CASE WHEN s.completed THEN 1 ELSE 0 END) = 1            THEN 'needs_retry'
                WHEN MAX(CASE WHEN NOT s.completed THEN 1 ELSE 0 END) = 1        THEN 'in_progress'
                ELSE 'not_started'
            END AS status,
            MAX(s.ended_at) AS last_attempt_at
        FROM progress_sessions s
        GROUP BY s.student_id, s.unit_id, s.curriculum_id, s.subject, s.grade
        WITH DATA
    """)

    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_progress_pk
            ON mv_student_curriculum_progress(student_id, unit_id, curriculum_id)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_mv_progress_student
            ON mv_student_curriculum_progress(student_id, curriculum_id)
    """)


def downgrade() -> None:
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_student_curriculum_progress")
    op.execute("DROP TABLE IF EXISTS lesson_views")
    op.execute("DROP TABLE IF EXISTS progress_answers")
    op.execute("DROP TABLE IF EXISTS progress_sessions")
