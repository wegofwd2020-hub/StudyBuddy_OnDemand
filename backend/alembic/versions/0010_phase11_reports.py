"""phase11_reports

Revision ID: 0010
Revises: 0009
Create Date: 2026-03-26

Phase 11 schema: teacher reporting dashboard.

Tables created:
  report_alert_settings  — per-school configurable thresholds
  digest_subscriptions   — teacher opt-in weekly email digest
  report_alerts          — triggered alert log

Materialized views created:
  mv_class_summary       — per (school_id, curriculum_id, unit_id) aggregated metrics
  mv_student_progress    — per (student_id, curriculum_id) completion + score rollup
  mv_feedback_summary    — per (curriculum_id, unit_id) feedback counts + avg rating

Refreshed nightly by Celery Beat (mv_class_summary, mv_student_progress),
hourly (mv_feedback_summary).
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── report_alert_settings ────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS report_alert_settings (
            school_id                  UUID        PRIMARY KEY REFERENCES schools(school_id) ON DELETE CASCADE,
            pass_rate_threshold        REAL        NOT NULL DEFAULT 50.0,
            feedback_count_threshold   INT         NOT NULL DEFAULT 3,
            inactive_days_threshold    INT         NOT NULL DEFAULT 14,
            score_drop_threshold       REAL        NOT NULL DEFAULT 10.0,
            new_feedback_immediate     BOOLEAN     NOT NULL DEFAULT TRUE,
            updated_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    # ── digest_subscriptions ─────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS digest_subscriptions (
            subscription_id UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            school_id       UUID        NOT NULL REFERENCES schools(school_id) ON DELETE CASCADE,
            teacher_id      UUID        NOT NULL REFERENCES teachers(teacher_id) ON DELETE CASCADE,
            email           TEXT        NOT NULL,
            timezone        TEXT        NOT NULL DEFAULT 'UTC',
            enabled         BOOLEAN     NOT NULL DEFAULT TRUE,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE(school_id, teacher_id)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_digest_school ON digest_subscriptions(school_id, enabled)")

    # ── report_alerts ────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS report_alerts (
            alert_id        UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            school_id       UUID        NOT NULL REFERENCES schools(school_id) ON DELETE CASCADE,
            alert_type      TEXT        NOT NULL,
            details         JSONB       NOT NULL DEFAULT '{}',
            triggered_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            acknowledged    BOOLEAN     NOT NULL DEFAULT FALSE
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_alerts_school ON report_alerts(school_id, acknowledged)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_alerts_triggered ON report_alerts(triggered_at DESC)")

    # ── mv_class_summary ─────────────────────────────────────────────────────
    # Per (school_id, curriculum_id, unit_id): lesson views, quiz attempts,
    # pass rates. Refreshed nightly by Celery Beat at 02:00 UTC.
    op.execute("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS mv_class_summary AS
        SELECT
            se.school_id,
            ps.curriculum_id,
            ps.unit_id,
            ps.subject,
            COUNT(DISTINCT lv.view_id)                                               AS lesson_views_total,
            COUNT(DISTINCT lv.student_id)                                            AS students_with_lesson_view,
            COUNT(DISTINCT ps.session_id)                                            AS quiz_attempts_total,
            COUNT(DISTINCT ps.student_id) FILTER (WHERE ps.completed)               AS students_attempted_quiz,
            ROUND(
                100.0 * COUNT(*) FILTER (WHERE ps.attempt_number = 1 AND ps.passed AND ps.completed)
                / NULLIF(COUNT(DISTINCT ps.student_id) FILTER (WHERE ps.attempt_number = 1 AND ps.completed), 0),
                1
            )                                                                        AS first_attempt_pass_rate_pct,
            ROUND(AVG(ps.score) FILTER (WHERE ps.completed)::numeric, 1)            AS avg_score_pct,
            ROUND(AVG(ps.attempt_number) FILTER (WHERE ps.passed AND ps.completed)::numeric, 1) AS avg_attempts_to_pass
        FROM school_enrolments se
        INNER JOIN progress_sessions ps ON ps.student_id = se.student_id
        LEFT JOIN lesson_views lv ON lv.student_id = ps.student_id AND lv.unit_id = ps.unit_id
        WHERE se.status = 'active' AND se.student_id IS NOT NULL
        GROUP BY se.school_id, ps.curriculum_id, ps.unit_id, ps.subject
        WITH DATA
    """)
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS mv_class_summary_pk ON mv_class_summary(school_id, curriculum_id, unit_id)")
    op.execute("CREATE INDEX IF NOT EXISTS mv_class_summary_school ON mv_class_summary(school_id)")

    # ── mv_student_progress ──────────────────────────────────────────────────
    # Per (student_id, curriculum_id): completion and score rollup.
    op.execute("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS mv_student_progress AS
        SELECT
            ps.student_id,
            ps.curriculum_id,
            COUNT(DISTINCT ps.unit_id) FILTER (WHERE ps.passed)      AS units_completed,
            ROUND(AVG(ps.score) FILTER (WHERE ps.completed)::numeric, 1) AS overall_avg_score_pct,
            COUNT(*) FILTER (WHERE ps.completed)                      AS quizzes_completed
        FROM progress_sessions ps
        GROUP BY ps.student_id, ps.curriculum_id
        WITH DATA
    """)
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS mv_student_progress_pk ON mv_student_progress(student_id, curriculum_id)")

    # ── mv_feedback_summary ──────────────────────────────────────────────────
    # Per (curriculum_id, unit_id): feedback counts and avg rating.
    # Refreshed hourly.
    op.execute("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS mv_feedback_summary AS
        SELECT
            COALESCE(curriculum_id, '')                           AS curriculum_id,
            COALESCE(unit_id, '')                                 AS unit_id,
            COUNT(*)                                              AS feedback_count,
            ROUND(AVG(rating)::numeric, 1)                        AS avg_rating,
            COUNT(*) FILTER (WHERE NOT reviewed)                  AS unreviewed_count,
            COUNT(*) FILTER (WHERE category = 'content')          AS content_count,
            COUNT(*) FILTER (WHERE category = 'ux')               AS ux_count,
            COUNT(*) FILTER (WHERE category = 'general')          AS general_count
        FROM feedback
        GROUP BY curriculum_id, unit_id
        WITH DATA
    """)
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS mv_feedback_summary_pk ON mv_feedback_summary(curriculum_id, unit_id)")


def downgrade() -> None:
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_feedback_summary")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_student_progress")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_class_summary")
    op.execute("DROP TABLE IF EXISTS report_alerts")
    op.execute("DROP TABLE IF EXISTS digest_subscriptions")
    op.execute("DROP TABLE IF EXISTS report_alert_settings")
