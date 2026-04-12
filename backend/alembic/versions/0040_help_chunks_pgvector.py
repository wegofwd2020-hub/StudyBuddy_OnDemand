"""0040 — Help system: help_chunks table with pgvector embeddings

Deliver-1: vector-search-based RAG retrieval for the POST /help/ask endpoint.

Requires the pgvector extension in PostgreSQL (available in the
pgvector/pgvector:pg16 Docker image used in docker-compose.yml).

New table
─────────
help_chunks
  chunk_id    UUID PK           generated per chunk
  persona     TEXT NOT NULL     'school_admin' | 'teacher' | 'student'
  source_file TEXT NOT NULL     relative path in the docs repo
  section_id  TEXT NOT NULL     HTML section id attribute (e.g. 'classrooms')
  heading     TEXT NOT NULL     h2 text extracted from the section
  body        TEXT NOT NULL     plain-text content of the section
  embedding   VECTOR(512)       voyage-3-lite embedding; NULL until index_help_library runs
  created_at  TIMESTAMPTZ

Index: ivfflat on embedding using cosine distance (lists=50 — tuned for ≤10k rows).

Note for developers
───────────────────
After running this migration, populate embeddings by running:
  docker compose exec api python scripts/index_help_library.py \\
      --library-path /path/to/studybuddy-docs/help

The endpoint degrades gracefully when VOYAGE_API_KEY is not set — it performs
a full text search over the body column instead of vector similarity.

Image change
────────────
The docker-compose.yml postgres image was updated from postgres:16-alpine to
pgvector/pgvector:pg16. Existing volumes must be rebuilt:
  docker compose down -v && docker compose up
"""

from alembic import op
import sqlalchemy as sa

revision = "0040"
down_revision = "0039"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Attempt to enable pgvector.  In production the pgvector/pgvector:pg16 image
    # is used and this always succeeds.  In CI / local dev the host postgres may
    # not have the extension; we catch the error and proceed without vector support.
    # The endpoint degrades gracefully to full-text search when pgvector is absent.
    op.execute("""
        DO $$
        BEGIN
            BEGIN
                EXECUTE 'CREATE EXTENSION IF NOT EXISTS vector';
            EXCEPTION WHEN OTHERS THEN
                NULL;  -- pgvector not installed; table will be created without it
            END;
        END $$
    """)

    # Create the table.  The embedding column is VECTOR(512) when pgvector is
    # available, and omitted otherwise (text-search fallback still works).
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN
                EXECUTE $sql$
                    CREATE TABLE IF NOT EXISTS help_chunks (
                        chunk_id    UUID         NOT NULL DEFAULT gen_random_uuid()
                                        PRIMARY KEY,
                        persona     TEXT         NOT NULL
                                        CHECK (persona IN ('school_admin', 'teacher', 'student')),
                        source_file TEXT         NOT NULL,
                        section_id  TEXT         NOT NULL,
                        heading     TEXT         NOT NULL,
                        body        TEXT         NOT NULL,
                        embedding   VECTOR(512),
                        created_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
                    )
                $sql$;
                EXECUTE $sql$
                    CREATE INDEX IF NOT EXISTS ix_help_chunks_embedding
                    ON help_chunks
                    USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = 50)
                    WHERE embedding IS NOT NULL
                $sql$;
            ELSE
                EXECUTE $sql$
                    CREATE TABLE IF NOT EXISTS help_chunks (
                        chunk_id    UUID         NOT NULL DEFAULT gen_random_uuid()
                                        PRIMARY KEY,
                        persona     TEXT         NOT NULL
                                        CHECK (persona IN ('school_admin', 'teacher', 'student')),
                        source_file TEXT         NOT NULL,
                        section_id  TEXT         NOT NULL,
                        heading     TEXT         NOT NULL,
                        body        TEXT         NOT NULL,
                        created_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
                    )
                $sql$;
            END IF;
        END $$
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_help_chunks_persona
        ON help_chunks (persona)
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS help_chunks CASCADE")
    # Leave the vector extension in place — removing it could break other tables.
