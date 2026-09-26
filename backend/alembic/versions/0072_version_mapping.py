"""0072_version_mapping: add version mapping table to link git tags to DB schemas.

Revision ID: 0072_version_mapping
Revises: 0071_inactive_students_alert
Create Date: 2026-09-26 21:20:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0072_version_mapping"
down_revision = "0071_inactive_students_alert"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "version_mapping",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("app_version", sa.Text(), nullable=False, comment="Git tag or semantic version"),
        sa.Column("db_schema_version", sa.Integer(), nullable=False, comment="Alembic migration version"),
        sa.Column("released_at", sa.Date(), nullable=False, comment="Release date"),
        sa.Column("notes", sa.Text(), nullable=True, comment="Release notes or migration notes"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("app_version", name="uq_version_mapping_app_version"),
    )

    # Create index for fast lookups by app_version
    op.create_index("idx_version_mapping_app_version", "version_mapping", ["app_version"])
    op.create_index("idx_version_mapping_db_schema", "version_mapping", ["db_schema_version"])

    # Insert initial mapping for current version
    op.execute(
        """
        INSERT INTO version_mapping (app_version, db_schema_version, released_at, notes)
        VALUES ('v0.2.0', 71, CURRENT_DATE, 'Initial version mapping')
        ON CONFLICT (app_version) DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_index("idx_version_mapping_db_schema", table_name="version_mapping")
    op.drop_index("idx_version_mapping_app_version", table_name="version_mapping")
    op.drop_table("version_mapping")
