"""
0016_teachers_nullable_school_id

Revision ID: 0016
Revises: 0015
Create Date: 2026-04-01

Makes school_id nullable on the teachers table.

Demo teacher accounts (auth_provider='demo') have no school affiliation and must
be insertable without a school_id.  All real teacher and school-admin queries
already filter by school_id explicitly, so making the column nullable has no
impact on those paths.
"""

from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE teachers
        ALTER COLUMN school_id DROP NOT NULL
    """)


def downgrade() -> None:
    # Remove demo teacher rows that have no school affiliation before reinstating
    # the NOT NULL constraint, otherwise the ALTER will fail.
    op.execute("""
        DELETE FROM teachers WHERE auth_provider = 'demo' AND school_id IS NULL
    """)
    op.execute("""
        ALTER TABLE teachers
        ALTER COLUMN school_id SET NOT NULL
    """)
