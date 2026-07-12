"""Add quiz_set to progress_sessions for server-side grading.

Quiz grading used to be done entirely by the client: `POST /progress/answer`
accepted a `correct: bool` and `POST /progress/session/{id}/end` accepted a
`score`, and the backend stored whatever the browser sent. A student could award
themselves a perfect score from the devtools console.

Grading server-side requires knowing WHICH quiz set the student is answering:
`question_id` is `q1`…`qN` in every set, but the correct option differs per set,
so the question id alone is not enough to look up the answer key. The server
already picks the set (round-robin, `get_next_quiz_set`); this column records
the choice on the session so the answer key can be resolved at grading time and
so the session remains auditable after the Redis rotation key expires.

Nullable: lesson/tutorial sessions have no quiz set.

Revision ID: 0061
Revises: 0060
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0061"
down_revision = "0060"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "progress_sessions",
        sa.Column("quiz_set", sa.SmallInteger(), nullable=True),
    )
    op.create_check_constraint(
        "ck_progress_sessions_quiz_set",
        "progress_sessions",
        "quiz_set IS NULL OR quiz_set BETWEEN 1 AND 3",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_progress_sessions_quiz_set", "progress_sessions", type_="check"
    )
    op.drop_column("progress_sessions", "quiz_set")
