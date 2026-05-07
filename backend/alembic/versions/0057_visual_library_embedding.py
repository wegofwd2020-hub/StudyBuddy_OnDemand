"""0057 — pgvector extension + embedding column for visual_library_entries (issue #321 / 319a part 2)

Adds the embedding column that the resolver in #323 (319c) will use for
semantic match between tutorial sections and library entries. Embeddings
are 512-dimensional cosine-distance vectors from Voyage AI's
`voyage-3-lite` model — matches the existing Voyage convention from
migration 0040 (help_chunks). The choice of model lives in
backend/src/visuals/library.py::compute_embedding().

Pre-requisite: pgvector installed on the PostgreSQL server. Dev:
`apt install postgresql-16-pgvector`. CI/prod: pgvector/pgvector:pg16
image already declared in docker-compose.yml.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0057"
down_revision: str | None = "0056"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Enable pgvector. Hard-fails clearly if the extension binary isn't
    # installed on the server.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.execute(
        "ALTER TABLE visual_library_entries "
        "ADD COLUMN IF NOT EXISTS embedding vector(512)"
    )

    # ivfflat index for cosine-similarity lookups. lists=100 is fine for
    # a corpus up to a few thousand entries; tune up when the library
    # grows past ~10k.
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS vle_embedding_ivfflat_idx
            ON visual_library_entries
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100)
            WHERE archived_at IS NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS vle_embedding_ivfflat_idx")
    op.execute(
        "ALTER TABLE visual_library_entries DROP COLUMN IF EXISTS embedding"
    )
    # Don't DROP EXTENSION — other migrations might add other vector
    # columns later. Leave it installed.
