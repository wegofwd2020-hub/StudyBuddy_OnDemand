"""0045_streams_registry

Soft registry for curriculum streams (Option C from the H-10 design).

Migration 0044 added free-text `stream_code` / `stream` columns. With the admin
Upload page about to make Stream mandatory and introduce an "Other…" custom-code
path, we need a canonical registry so admins can:
  - see which streams exist across the platform
  - rename / merge near-duplicates (e.g. `Commerce` vs `commerce` vs `COMM.`)
  - archive streams that are no longer in use

Deliberately **no FK** from curricula / students / teachers into `streams.code`.
Keeps the migration risk low, lets legacy stream-unaware rows (NULL) continue to
work without a registry entry, and makes rename/merge a data action without
touching constraints. `curricula_count` is a denormalised lookup refreshed on
upsert-on-use by the application layer (S-2).

Revision ID: 0045
Revises: 0044
"""

from alembic import op
import sqlalchemy as sa


revision = "0045"
down_revision = "0044"
branch_labels = None
depends_on = None


_SYSTEM_STREAMS = [
    (
        "science",
        "Science",
        "CBSE Science stream — Physics, Chemistry, Mathematics, Biology",
    ),
    (
        "commerce",
        "Commerce",
        "CBSE Commerce — Accountancy, Business Studies, Economics",
    ),
    (
        "humanities",
        "Humanities",
        "CBSE Humanities — History, Political Science, Geography, Psychology/Sociology",
    ),
    (
        "english",
        "English Core",
        "Standalone English Core",
    ),
    (
        "stem",
        "STEM (legacy US)",
        "Legacy US-style mixed Math/Science/Technology",
    ),
]


def upgrade() -> None:
    op.create_table(
        "streams",
        sa.Column("code", sa.Text(), primary_key=True),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "is_system",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "is_archived",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "curricula_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "created_by_admin_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("admin_users.admin_user_id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_streams_is_archived",
        "streams",
        ["is_archived"],
        postgresql_where=sa.text("is_archived = false"),
    )

    conn = op.get_bind()

    for code, display_name, description in _SYSTEM_STREAMS:
        conn.execute(
            sa.text(
                """
                INSERT INTO streams (code, display_name, description, is_system)
                VALUES (:code, :display_name, :description, true)
                ON CONFLICT (code) DO NOTHING
                """
            ),
            {
                "code": code,
                "display_name": display_name,
                "description": description,
            },
        )

    # Capture any stream_code values that exist on curricula but are not in the
    # system seed list — insert them as non-system rows so the registry is a
    # complete view of reality post-migration.
    conn.execute(
        sa.text(
            """
            INSERT INTO streams (code, display_name, is_system)
            SELECT DISTINCT
                   c.stream_code,
                   initcap(c.stream_code),
                   false
              FROM curricula c
             WHERE c.stream_code IS NOT NULL
               AND c.stream_code NOT IN (SELECT code FROM streams)
            ON CONFLICT (code) DO NOTHING
            """
        )
    )

    conn.execute(
        sa.text(
            """
            UPDATE streams s
               SET curricula_count = (
                   SELECT COUNT(*)
                     FROM curricula c
                    WHERE c.stream_code = s.code
               )
            """
        )
    )


def downgrade() -> None:
    op.drop_index("ix_streams_is_archived", table_name="streams")
    op.drop_table("streams")
