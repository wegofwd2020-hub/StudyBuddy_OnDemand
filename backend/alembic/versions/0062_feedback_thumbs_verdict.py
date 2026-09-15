"""Let the lesson thumbs widget store a verdict with no written message.

The `feedback` table was built for written feedback: `message` NOT NULL with an
optional 1-5 star `rating`. The thumbs up/down control on lesson, tutorial and
experiment pages has no text box, so it could never satisfy that shape — every
submission failed and the table held zero rows for the life of the deployment
(issue #600).

Two ways to reconcile that. We could have synthesised message text ("Thumbs up
on lesson") client-side, but the admin review list presents `message` as the
student's own words, so inventing it would put words in a student's mouth. The
honest option is to let a verdict stand on its own:

- `message`   becomes nullable  — a thumbs vote carries no prose
- `helpful`   records the verdict itself, distinct from the 1-5 `rating` so a
              thumbs-up is never displayed as "5 stars" the student never chose
- `content_type` records what was rated; `unit_id` alone cannot distinguish a
              lesson from its tutorial

`feedback_has_content` then replaces the NOT NULL as the thing that keeps blank
rows out: a row must carry at least one of message, rating or verdict. Relaxing
the column without it would let empty feedback accumulate silently.

Revision ID: 0062
Revises: 0061
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0062"
down_revision = "0061"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("feedback", "message", existing_type=sa.Text(), nullable=True)
    op.add_column("feedback", sa.Column("helpful", sa.Boolean(), nullable=True))
    op.add_column("feedback", sa.Column("content_type", sa.Text(), nullable=True))
    op.create_check_constraint(
        "feedback_content_type_check",
        "feedback",
        "content_type IS NULL OR content_type IN ('lesson', 'tutorial', 'experiment', 'quiz')",
    )
    op.create_check_constraint(
        "feedback_has_content",
        "feedback",
        "message IS NOT NULL OR rating IS NOT NULL OR helpful IS NOT NULL",
    )


def downgrade() -> None:
    op.drop_constraint("feedback_has_content", "feedback", type_="check")
    op.drop_constraint("feedback_content_type_check", "feedback", type_="check")
    # Rows that only ever had a verdict have no message to restore, and the
    # column is about to be NOT NULL again — drop them rather than invent text.
    op.execute("DELETE FROM feedback WHERE message IS NULL")
    op.drop_column("feedback", "content_type")
    op.drop_column("feedback", "helpful")
    op.alter_column("feedback", "message", existing_type=sa.Text(), nullable=False)
