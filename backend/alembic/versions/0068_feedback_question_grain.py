"""0068 — let feedback point at a QUESTION, not just a unit (ADR-008 Phase 2).

`feedback` is keyed by `unit_id` and `content_type`. A student can say "this
lesson wasn't helpful"; nobody can say **"question 4 is wrong."**

That missing sentence is the highest-value signal in ADR-008. Decision 8's
statistics can tell you a question is behaving oddly — a question the strong
students miss more often than the weak ones is broken rather than hard — but a
statistic needs a few dozen responses before it means anything, and it can never
say WHY. A person who just read the question can, immediately, on the first
encounter.

## Nullable, because most feedback is not about a question

Feedback on a lesson or a tutorial has no question to point at, and the existing
thumbs widget (#600/#612) submits with no question either. So this is an optional
narrowing of existing feedback, not a new required field, and every current
submission path keeps working untouched.

## The value is a STABLE question id, not a positional one

`q1…qN` names a slot within a quiz set (see migration 0067). Storing that would
attach a comment to "the first question of whichever set this was", which is not
a thing anyone can act on. The column holds the content-addressed identity from
`src/core/question_identity.py`, so a flag raised against a question in set 1
sits alongside the answers recorded for that same question reached through set 3.

The API deliberately does NOT accept this id from the client. A student's client
sends the positional id it was shown plus its session, and the server resolves the
stable id from the set that session was graded against — the same shape as the
answer path, and for the same reason: the client should not be able to name a
question it was never served.

## Downgrade drops student-authored content

Unlike 0067, whose value is a pure function of content and therefore recomputable,
a comment attached to a question is something a person wrote. Dropping this column
destroys it. The downgrade is written for completeness and a real rollback should
export the column first.

Revision ID: 0068
Revises: 0067
"""

from alembic import op

revision = "0068"
down_revision = "0067"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE feedback ADD COLUMN IF NOT EXISTS stable_question_id TEXT")

    # Partial: only a minority of feedback rows will ever name a question, and
    # every query that wants them wants exactly those.
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_feedback_stable_question
            ON feedback (stable_question_id)
            WHERE stable_question_id IS NOT NULL
        """
    )


def downgrade() -> None:
    # DESTRUCTIVE: drops comments a student wrote. Export before rolling back.
    op.execute("DROP INDEX IF EXISTS idx_feedback_stable_question")
    op.execute("ALTER TABLE feedback DROP COLUMN IF EXISTS stable_question_id")
