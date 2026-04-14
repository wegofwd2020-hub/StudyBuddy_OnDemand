"""0044_stream_column

Add nullable `stream` layer between Grade and Subject.

Context: some curriculum systems (CBSE India, IB, A-Levels) partition subjects
at a given grade into Streams — Science, Commerce, Humanities, English — and
each student belongs to exactly one stream. The data model has Grade → Subject
today with no way to express this grouping.

Rather than introduce a full Stream entity with its own table and FK graph,
Stream becomes a scoping attribute on:
  - curricula.stream_code     — identifies which stream a curriculum is for
  - students.stream           — which stream the student is enrolled in
  - teachers.stream           — which stream a teacher is assigned to (optional)

All columns are nullable. Existing US-STEM curricula and all currently-enrolled
users continue to work as "stream-unaware" (NULL stream). Streams are opt-in
per curriculum.

Canonical stream codes (not enforced as enum — free text for now, validation
lives at the application layer so adding new streams doesn't need a migration):
  - 'science'
  - 'commerce'
  - 'humanities'
  - 'english'
  - 'stem'        (legacy US-style mixed Math+Science)

Revision ID: 0044
Revises: 0043
"""

from alembic import op
import sqlalchemy as sa

revision = "0044"
down_revision = "0043"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "curricula",
        sa.Column("stream_code", sa.Text(), nullable=True),
    )
    op.add_column(
        "students",
        sa.Column("stream", sa.Text(), nullable=True),
    )
    op.add_column(
        "teachers",
        sa.Column("stream", sa.Text(), nullable=True),
    )

    # Index on curricula.stream_code — used for stream-filtered catalog listings
    # and the "find curriculum for (grade, stream)" lookup the pipeline trigger
    # will use once streams are wired in.
    op.create_index(
        "ix_curricula_grade_stream",
        "curricula",
        ["grade", "stream_code"],
    )

    # Index on students.stream — used for per-stream roster filtering.
    op.create_index(
        "ix_students_stream",
        "students",
        ["school_id", "stream"],
    )


def downgrade() -> None:
    op.drop_index("ix_students_stream", table_name="students")
    op.drop_index("ix_curricula_grade_stream", table_name="curricula")
    op.drop_column("teachers", "stream")
    op.drop_column("students", "stream")
    op.drop_column("curricula", "stream_code")
