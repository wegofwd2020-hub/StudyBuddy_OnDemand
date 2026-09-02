"""0069 — the question registry (ADR-008 Phase 3a).

Phases 1 and 2 gave a question a stable identity and let a person point at one.
Neither gave the platform anywhere to KEEP a question. Bodies live in the content
store, addressed by set file, and the only way to enumerate a unit's questions is
to open `quiz_set_1/2/3` and read them. That is why a quiz is a fixed set: there
is no list to draw from.

This table is that list — one row per distinct question per unit, keyed by the
content-addressed identity from migration 0067. It deliberately does NOT hold the
question body (Decision 5): bodies stay in the content store, and the registry
holds identity, provenance and lifecycle. Two reasons that split is worth keeping:
a body is large and versioned by the store already, and a registry row must
survive a body being rewritten (a rewrite mints a NEW id per the corrected
Decision 4, and the registry is where that succession can eventually be recorded).

## What it enables immediately

Phase 3a draws a quiz from the registry instead of serving a fixed set. Measured
over real platform content: a unit has a median of 24 distinct questions, so
drawing 8 gives on the order of 10^5 distinct quizzes where there were 3. That is
the whole of the tester's "reduces the predictability" ask, at zero generation
cost — the questions already exist.

## Why the columns are what they are

`stable_question_id` is the primary key, not a surrogate. The id IS the identity
(sha256 over curriculum|unit|lang|stem), so a surrogate would add a second way to
say the same thing and a way for the two to disagree.

`curriculum_id` + `unit_id` + `lang` are stored even though they are inputs to the
id, because every query wants to filter by them and re-deriving is not possible
from the hash.

`difficulty` is denormalised from the body so the stratified draw (Decision 7) is
one indexed query rather than a fan-out into the content store. It is nullable:
the generator populates it today, but a question whose body lacks it must still
be registrable rather than silently dropped.

`status` carries lifecycle. 'active' is drawable; 'retired' is kept for the
statistics already attached to it (Decision 8) but never served again. Retiring
rather than deleting is the point — deleting a question destroys the answer
history that made it worth retiring.

`source_set` records which quiz_set file a backfilled question came from. Purely
provenance: it makes the backfill auditable and lets a bad import be undone
without guessing.

## Scope

Rows are per (curriculum, unit, lang), and `curriculum_id` is already the tenancy
boundary for content — a school fork has its own curriculum_id. No RLS policy is
added here for the same reason `curriculum_units` has none: this is content
metadata, not tenant data, and the serving path already resolves which curriculum
a student may read.

Downgrade drops the table. That is safe in a way 0068's downgrade was not: every
row is derivable again from the content store by re-running the backfill, because
the identity is a pure function of content.

Revision ID: 0069
Revises: 0068
"""

from alembic import op

revision = "0069"
down_revision = "0068"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS question_registry (
            stable_question_id  TEXT        PRIMARY KEY,
            curriculum_id       TEXT        NOT NULL,
            unit_id             TEXT        NOT NULL,
            lang                TEXT        NOT NULL DEFAULT 'en',
            difficulty          TEXT,
            status              TEXT        NOT NULL DEFAULT 'active',
            source_set          SMALLINT,
            first_seen_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT question_registry_status_check
                CHECK (status IN ('active', 'retired')),
            CONSTRAINT question_registry_difficulty_check
                CHECK (difficulty IS NULL OR difficulty IN ('easy', 'medium', 'hard'))
        )
        """
    )

    # The draw's own query: every active question for one unit in one language,
    # narrowed by difficulty for the stratified pick. Partial on 'active' because
    # a retired question is never drawn and there is no point carrying it in the
    # index the hot path uses.
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_question_registry_draw
            ON question_registry (curriculum_id, unit_id, lang, difficulty)
            WHERE status = 'active'
        """
    )

    # Backfill and audit go the other way round — "what did this unit import,
    # including anything since retired" — so it cannot reuse the partial index.
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_question_registry_unit
            ON question_registry (curriculum_id, unit_id)
        """
    )


def downgrade() -> None:
    # Safe to drop: every row is a pure function of content in the store, so the
    # backfill reconstructs it exactly. Unlike 0068, nothing here was authored by
    # a person.
    op.execute("DROP INDEX IF EXISTS idx_question_registry_unit")
    op.execute("DROP INDEX IF EXISTS idx_question_registry_draw")
    op.execute("DROP TABLE IF EXISTS question_registry")
