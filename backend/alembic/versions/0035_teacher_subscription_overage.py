"""0035 — teacher_subscription_overage

Adds over-quota tracking columns to teacher_subscriptions so the
check_teacher_seat_quotas Celery Beat task can flag independent teachers
who have exceeded their plan's student cap.

Schema changes
──────────────
teacher_subscriptions
  over_quota        BOOLEAN NOT NULL DEFAULT FALSE
                    Set TRUE by the daily seat-quota Beat task when
                    seats_used > max_students.  Cleared on plan upgrade
                    or when seats_used drops back within the limit.

  over_quota_since  TIMESTAMPTZ NULL
                    Timestamp when over_quota was first set.  Used to
                    enforce the 7-day grace period before content access
                    is restricted.  NULL when over_quota = FALSE.

Revision ID: 0035
Revises: 0034
Create Date: 2026-04-10
"""

from alembic import op

revision = "0035"
down_revision = "0034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE teacher_subscriptions
            ADD COLUMN IF NOT EXISTS over_quota       BOOLEAN     NOT NULL DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS over_quota_since TIMESTAMPTZ
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_teacher_subscriptions_over_quota
            ON teacher_subscriptions (teacher_id)
            WHERE over_quota = TRUE
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP INDEX IF EXISTS idx_teacher_subscriptions_over_quota"
    )
    op.execute(
        """
        ALTER TABLE teacher_subscriptions
            DROP COLUMN IF EXISTS over_quota,
            DROP COLUMN IF EXISTS over_quota_since
        """
    )
