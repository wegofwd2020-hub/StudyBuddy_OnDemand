"""0067 — record which QUESTION an answer was to (ADR-008 Phase 1).

`progress_answers.question_id` holds `q1…qN`, a position **within a quiz set**.
`q1` of set 2 is a different question from `q1` of set 1 in the same unit, so the
column identifies a slot rather than a question. Everything already being
collected through it — the verdict, and `ms_taken` — therefore cannot be grouped
by anything meaningful: `GROUP BY question_id` groups questions that merely share
an index.

That is the one thing blocking every other part of ADR-008. Item analysis
(Decision 8) is a statement about a question; without an identity for a question
there is nothing to make the statement about.

`stable_question_id` carries the content-addressed identity from
`pipeline/question_identity.py` — a hash of `curriculum_id | unit_id | lang |
question stem`. The same question reached through set 1 and set 3 lands on one
id, which is the point.

## Nullable, and pre-migration rows stay NULL

Existing rows are **not back-fillable**. Recovering which question an old `q3`
referred to would need the quiz set that session was graded against, and while
`progress_sessions.quiz_set` exists (migration 0061) it was only added partway
through the history — earlier sessions have no set recorded, and content has been
regenerated since in ways that would silently mis-attribute the rest.

So the column is nullable and old answers keep NULL. Any item analysis must filter
`WHERE stable_question_id IS NOT NULL` rather than treat NULL as a group: mixing
pre- and post-migration answers would produce statistics whose denominators are
part slot and part question. Stated here because "just exclude the nulls" is the
kind of instruction that gets lost between a migration and the query that needs it.

## Downgrade is unusually safe

Dropping this column loses no information that cannot be recomputed: the value is
a pure function of content that still exists on disk, so re-running the backfill
after a re-upgrade reproduces it exactly. That is a property of content-addressing,
not a general licence — most dropped columns are not recoverable.

Revision ID: 0067
Revises: 0066
"""

from alembic import op

revision = "0067"
down_revision = "0066"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE progress_answers ADD COLUMN IF NOT EXISTS stable_question_id TEXT")

    # Partial: every pre-migration row is NULL and no analytic query wants them,
    # so they are kept out of the index entirely rather than bloating it.
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_answers_stable_question
            ON progress_answers (stable_question_id)
            WHERE stable_question_id IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_answers_stable_question")
    op.execute("ALTER TABLE progress_answers DROP COLUMN IF EXISTS stable_question_id")
