"""School localization — currency, timezone, number formatting.

Revision ID: 0073
Revises: 0072
Create Date: 2026-09-20 10:40:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0073"
down_revision = "0072"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "school_localization",
        sa.Column("school_id", sa.UUID(), nullable=False),
        sa.Column("country_code", sa.String(2), nullable=False, comment="ISO 3166-1 alpha-2"),
        sa.Column("currency_code", sa.String(3), nullable=False, comment="ISO 4217"),
        sa.Column("currency_symbol", sa.String(10), nullable=False),
        sa.Column("thousands_separator", sa.String(1), nullable=False),
        sa.Column("decimal_separator", sa.String(1), nullable=False),
        sa.Column("timezone", sa.String(63), nullable=False, comment="IANA timezone"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(["school_id"], ["schools.school_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("school_id"),
    )
    op.create_index("ix_school_localization_country", "school_localization", ["country_code"])


def downgrade() -> None:
    op.drop_index("ix_school_localization_country", table_name="school_localization")
    op.drop_table("school_localization")
