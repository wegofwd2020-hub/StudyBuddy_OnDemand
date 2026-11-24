"""0075_normalize_email_lowercase: store teacher, student and enrolment emails lowercased.

Revision ID: 0075
Revises: 0074
Create Date: 2026-11-24 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0075"
down_revision = "0074"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SELECT set_config('app.current_school_id', 'bypass', false)")

    clashes = (
        op.get_bind()
        .execute(
            sa.text(
                """
                SELECT 'teachers' AS tbl, lower(email) AS key
                  FROM teachers GROUP BY lower(email) HAVING count(*) > 1
                UNION ALL
                SELECT 'students', lower(email)
                  FROM students GROUP BY lower(email) HAVING count(*) > 1
                UNION ALL
                SELECT 'school_enrolments', school_id::text || ' ' || lower(student_email)
                  FROM school_enrolments
                 GROUP BY school_id, lower(student_email) HAVING count(*) > 1
                """
            )
        )
        .fetchall()
    )
    if clashes:
        raise RuntimeError(
            "Cannot lowercase emails: case-only duplicates exist "
            f"({', '.join(f'{tbl}: {key}' for tbl, key in clashes)}). "
            "Resolve them manually, then re-run the migration."
        )

    op.execute("UPDATE teachers SET email = lower(email) WHERE email <> lower(email)")
    op.execute("UPDATE students SET email = lower(email) WHERE email <> lower(email)")
    op.execute(
        "UPDATE school_enrolments SET student_email = lower(student_email) "
        "WHERE student_email <> lower(student_email)"
    )


def downgrade() -> None:
    # The original letter case is not recorded, so it cannot be restored.
    pass
