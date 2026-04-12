"""0038 — Phase B: Classrooms

Introduces the Classroom entity — the binding between a set of students and
one or more Curriculum Packages (curricula rows).

New tables
──────────
classrooms
  classroom_id   UUID PK
  school_id      UUID FK → schools
  teacher_id     UUID FK → teachers (nullable — classroom may have no lead teacher)
  name           TEXT NOT NULL
  grade          INT  (nullable — cross-grade classrooms allowed)
  status         TEXT 'active' | 'archived'
  created_at     TIMESTAMPTZ

classroom_packages   (many-to-many: classroom ↔ curricula)
  classroom_id   UUID FK → classrooms   }  PK
  curriculum_id  UUID FK → curricula    }
  assigned_at    TIMESTAMPTZ
  assigned_by    UUID (no FK — could be teacher_id or admin_id)
  sort_order     INT NOT NULL DEFAULT 0

classroom_students   (many-to-many: classroom ↔ students)
  classroom_id   UUID FK → classrooms   }  PK
  student_id     UUID FK → students     }
  joined_at      TIMESTAMPTZ

RLS: all three tables enable RLS and inherit the existing tenant isolation
     policy pattern — app.current_school_id controls row visibility.

Revision ID: 0038
Revises: 0037
Create Date: 2026-04-12
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0038"
down_revision: Union[str, None] = "0037"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── classrooms ────────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS classrooms (
            classroom_id  UUID         NOT NULL DEFAULT gen_random_uuid(),
            school_id     UUID         NOT NULL REFERENCES schools(school_id)
                              ON DELETE CASCADE,
            teacher_id    UUID         REFERENCES teachers(teacher_id)
                              ON DELETE SET NULL,
            name          TEXT         NOT NULL,
            grade         INT,
            status        TEXT         NOT NULL DEFAULT 'active'
                              CHECK (status IN ('active', 'archived')),
            created_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
            PRIMARY KEY (classroom_id)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_classrooms_school_id ON classrooms(school_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_classrooms_teacher_id ON classrooms(teacher_id)")

    # ── classroom_packages ────────────────────────────────────────────────────
    # curriculum_id is TEXT (matching curricula.curriculum_id TEXT PK).
    # No FK constraint — curricula IDs include platform IDs like "default-2026-g8"
    # that may not be present in every environment, and application logic is the
    # enforcement layer for referential integrity here.
    op.execute("""
        CREATE TABLE IF NOT EXISTS classroom_packages (
            classroom_id  UUID         NOT NULL REFERENCES classrooms(classroom_id)
                              ON DELETE CASCADE,
            curriculum_id TEXT         NOT NULL,
            assigned_at   TIMESTAMPTZ  NOT NULL DEFAULT now(),
            assigned_by   UUID,
            sort_order    INT          NOT NULL DEFAULT 0,
            PRIMARY KEY (classroom_id, curriculum_id)
        )
    """)

    # ── classroom_students ────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS classroom_students (
            classroom_id  UUID         NOT NULL REFERENCES classrooms(classroom_id)
                              ON DELETE CASCADE,
            student_id    UUID         NOT NULL REFERENCES students(student_id)
                              ON DELETE CASCADE,
            joined_at     TIMESTAMPTZ  NOT NULL DEFAULT now(),
            PRIMARY KEY (classroom_id, student_id)
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_classroom_students_student_id "
        "ON classroom_students(student_id)"
    )

    # ── RLS ───────────────────────────────────────────────────────────────────
    # classrooms — filter by school_id (same pattern as schools, teachers, students)
    op.execute("ALTER TABLE classrooms ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE classrooms FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON classrooms
            USING (
                school_id::TEXT = current_setting('app.current_school_id', TRUE)
                OR current_setting('app.current_school_id', TRUE) = 'bypass'
            )
    """)

    # classroom_packages — join via classrooms to inherit tenant scope
    op.execute("ALTER TABLE classroom_packages ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE classroom_packages FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON classroom_packages
            USING (
                EXISTS (
                    SELECT 1 FROM classrooms c
                    WHERE c.classroom_id = classroom_packages.classroom_id
                      AND (
                          c.school_id::TEXT = current_setting('app.current_school_id', TRUE)
                          OR current_setting('app.current_school_id', TRUE) = 'bypass'
                      )
                )
            )
    """)

    # classroom_students — join via classrooms to inherit tenant scope
    op.execute("ALTER TABLE classroom_students ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE classroom_students FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON classroom_students
            USING (
                EXISTS (
                    SELECT 1 FROM classrooms c
                    WHERE c.classroom_id = classroom_students.classroom_id
                      AND (
                          c.school_id::TEXT = current_setting('app.current_school_id', TRUE)
                          OR current_setting('app.current_school_id', TRUE) = 'bypass'
                      )
                )
            )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS classroom_students CASCADE")
    op.execute("DROP TABLE IF EXISTS classroom_packages CASCADE")
    op.execute("DROP TABLE IF EXISTS classrooms CASCADE")
