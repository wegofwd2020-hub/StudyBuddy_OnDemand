"""0056 — visual_library_entries (issue #321 / 319a)

Platform-curated visual library. Each row references a SVG/PNG/MP4 asset
under ${CONTENT_STORE_PATH}/visual_library/{subject}/{slug}.{ext}, plus
metadata that the pipeline resolver uses for semantic match.

This migration ships WITHOUT the pgvector embedding column. A follow-up
migration (0057) will add it once pgvector is installed on the dev DB
(host PG needs `apt install postgresql-16-pgvector`; CI/prod use the
pgvector/pgvector:pg16 image already declared in docker-compose.yml).
The Pydantic LibraryEntry model in src/visuals/library.py already
declares `embedding: list[float] | None` so adding the column is
non-breaking.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0056"
down_revision: str | None = "0055"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS visual_library_entries (
            entry_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            kind              TEXT NOT NULL CHECK (kind IN
                                  ('image', 'image-grid', 'animated-svg', 'video')),
            subject           TEXT NOT NULL,
            topic_phrase      TEXT NOT NULL,
            keywords          TEXT[] NOT NULL DEFAULT '{}',
            s3_path           TEXT NOT NULL,
            s3_metadata_path  TEXT,
            license           TEXT NOT NULL DEFAULT 'platform-cc-by-sa',
            source_unit       TEXT,
            archived_at       TIMESTAMPTZ,
            created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )

    # Soft-unique on s3_path among non-archived rows: re-promotion of the same
    # asset replaces the row rather than creating duplicates.
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS vle_s3_path_active_idx
            ON visual_library_entries (s3_path)
            WHERE archived_at IS NULL
        """
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS vle_subject_topic_idx
            ON visual_library_entries (subject, topic_phrase)
            WHERE archived_at IS NULL
        """
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS vle_keywords_gin_idx
            ON visual_library_entries USING gin (keywords)
            WHERE archived_at IS NULL
        """
    )

    # ── RLS — visual_library_entries ──────────────────────────────────────────
    # Library is platform-owned. Schools read; only bypass sessions write.
    op.execute("ALTER TABLE visual_library_entries ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE visual_library_entries FORCE ROW LEVEL SECURITY")

    # All authenticated sessions can read non-archived entries.
    # Bypass also reads archived (so admin UI can list them).
    op.execute(
        """
        CREATE POLICY public_read ON visual_library_entries FOR SELECT
            USING (
                archived_at IS NULL
                OR current_setting('app.current_school_id', TRUE) = 'bypass'
            )
        """
    )

    # Only bypass sessions can mutate.
    op.execute(
        """
        CREATE POLICY platform_write ON visual_library_entries FOR ALL
            USING (current_setting('app.current_school_id', TRUE) = 'bypass')
            WITH CHECK (current_setting('app.current_school_id', TRUE) = 'bypass')
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS visual_library_entries CASCADE")
