"""0046_platform_readable_rls

Formalise the "default library" access model at the database level (Epic 10
phase L-1, scaled-back scope).

`curricula` already has RLS + FORCE enabled (migration 0028) with a single FOR
ALL `tenant_isolation` policy that allows school sessions to see platform rows
but also lets them UPDATE or DELETE in principle (only blocked today by
endpoint-level checks).

This migration adds three RESTRICTIVE policies on `curricula` — one each for
INSERT / UPDATE / DELETE — that refuse mutations of `owner_type='platform'`
rows unless the session is super-admin (`app.current_school_id = 'bypass'`).
The existing permissive policy continues to handle SELECT visibility, so
schools can still read the default library without change.

Scope note: the ticket (Epic 10 L-1) also asks for equivalent RLS on
`curriculum_units` and `content_subject_versions`. That piece is deferred to
a follow-up because it requires a change to the test pool setup (asyncpg
`setup` callback reliability with `pool.fetchrow`) and a test DB recreation.
Tracked as `docs/epics/EPIC_10_curriculum_lifecycle.md` L-1-follow-up.

Revision ID: 0046
Revises: 0045
"""

from alembic import op


revision = "0046"
down_revision = "0045"
branch_labels = None
depends_on = None


def upgrade() -> None:
    write_guard = (
        "owner_type <> 'platform' "
        "OR COALESCE(current_setting('app.current_school_id', true), '') = 'bypass'"
    )

    # Three per-command restrictive policies. Deliberately NOT FOR ALL —
    # FOR ALL would gate SELECT as well and block schools from reading the
    # default library, which is the opposite of what we want.
    op.execute(
        f"CREATE POLICY no_write_platform_curricula_insert ON curricula "
        f"AS RESTRICTIVE FOR INSERT WITH CHECK ({write_guard})"
    )
    op.execute(
        f"CREATE POLICY no_write_platform_curricula_update ON curricula "
        f"AS RESTRICTIVE FOR UPDATE USING ({write_guard}) WITH CHECK ({write_guard})"
    )
    op.execute(
        f"CREATE POLICY no_write_platform_curricula_delete ON curricula "
        f"AS RESTRICTIVE FOR DELETE USING ({write_guard})"
    )


def downgrade() -> None:
    for cmd in ("insert", "update", "delete"):
        op.execute(
            f"DROP POLICY IF EXISTS no_write_platform_curricula_{cmd} ON curricula"
        )
