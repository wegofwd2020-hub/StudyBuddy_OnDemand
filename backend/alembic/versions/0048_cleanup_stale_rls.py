"""0048_cleanup_stale_rls

Drop stale RLS policies left on `curriculum_units` and `content_subject_versions`
by an earlier draft of Epic 10 L-1 (migration 0046 before it was scaled back
to Option 3). The draft enabled RLS + FORCE + per-command restrictive
policies on both child tables; the shipped migration 0046 only touches
`curricula` and never added corresponding down-steps for the orphans.

As a result the dev DB carried four policies and RLS+FORCE flags on each
child table that the codebase expected to be absent. The symptoms:

  - Pipeline DB upsert of content_subject_versions silently fails with
    "new row violates row-level security policy
    no_write_platform_versions_insert" — writing content files succeeds
    but the review-queue row never lands.
  - Test helpers that seed content_subject_versions directly via
    pool.execute fail with the same error unless the pool connection is
    pre-stamped as 'bypass'.

This migration is idempotent — it drops policies IF EXISTS and disables
RLS / FORCE flags. Safe to apply on any environment regardless of
whether the stale state was ever installed.

Revision ID: 0048
Revises: 0047
"""

from alembic import op


revision = "0048"
down_revision = "0047"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop any stale policies the 0046 draft left behind.
    for table, prefix in [
        ("curriculum_units", "no_write_platform_units"),
        ("content_subject_versions", "no_write_platform_versions"),
    ]:
        # Per-command variants (INSERT / UPDATE / DELETE).
        for cmd in ("insert", "update", "delete"):
            op.execute(f"DROP POLICY IF EXISTS {prefix}_{cmd} ON {table}")
        # Tenant-visibility policy from the draft.
        op.execute(f"DROP POLICY IF EXISTS tenant_via_curriculum ON {table}")
        # FOR ALL variant that predated the per-command split.
        op.execute(f"DROP POLICY IF EXISTS {prefix} ON {table}")
        # Disable RLS + FORCE so the tables behave as pre-0046.
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    # Nothing to restore — this migration only removes state that
    # shouldn't have been there. Re-applying the stale state is not a
    # legitimate rollback target.
    pass
