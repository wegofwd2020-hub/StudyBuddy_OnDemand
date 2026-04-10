"""
0021_curricula_school_source_type

Revision ID: 0021
Revises: 0020
Create Date: 2026-04-01

Extends the curricula.source_type CHECK constraint to include 'school',
enabling school-uploaded grade JSON curricula to be distinguished from
default platform content and XLSX/UI-form uploads.

Before: source_type IN ('default', 'xlsx_upload', 'ui_form')
After:  source_type IN ('default', 'xlsx_upload', 'ui_form', 'school')
"""

from alembic import op

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE curricula DROP CONSTRAINT IF EXISTS curricula_source_type_check")
    op.execute("""
        ALTER TABLE curricula
            ADD CONSTRAINT curricula_source_type_check
            CHECK (source_type IN ('default', 'xlsx_upload', 'ui_form', 'school'))
    """)


def downgrade() -> None:
    # Re-label school rows before tightening the constraint so existing data
    # doesn't violate the restored CHECK on ('default', 'xlsx_upload', 'ui_form').
    op.execute("UPDATE curricula SET source_type = 'ui_form' WHERE source_type = 'school'")
    op.execute("ALTER TABLE curricula DROP CONSTRAINT IF EXISTS curricula_source_type_check")
    op.execute("""
        ALTER TABLE curricula
            ADD CONSTRAINT curricula_source_type_check
            CHECK (source_type IN ('default', 'xlsx_upload', 'ui_form'))
    """)
