---
description: Scaffold a new Alembic migration with RLS checklist and downgrade-cycle reminder.
---

You are creating a new Alembic migration named: **$ARGUMENTS**

## Step 1 — Determine the next number

Run:
```bash
ls backend/alembic/versions/ | grep -E '^[0-9]{4}_' | sort | tail -1
```

Take the last number, increment by 1, zero-pad to 4 digits. Example: if the last is `0048_*`, the new file is `00NN_<slug>.py`.

The slug should be `snake_case`, derived from the argument (e.g., "add user prefs table" → `add_user_prefs_table`). Keep it under ~35 chars.

## Step 2 — Read the most recent migration for pattern reference

Pick one from the last 5 that resembles your case:
- Add/alter columns → `0024_student_teacher_assignments.py`
- RLS changes → `0028_row_level_security.py` or `0046_platform_readable_rls.py`
- Seed rows → `0045_streams_registry.py`
- Cleanup/hotfix → `0048_cleanup_stale_rls.py`

Use its structure (revision id, down_revision, upgrade/downgrade shape) as the template.

## Step 3 — Write the migration

Before writing, answer these out loud:

1. **What schema change?** Tables / columns / indexes / constraints / policies.
2. **RLS needed?** If the table is tenant-scoped (has `school_id` or equivalent), it MUST have:
   - `ENABLE ROW LEVEL SECURITY` + `FORCE ROW LEVEL SECURITY`
   - A policy referencing `current_setting('app.current_school_id', true)`
   - Consider whether the session `bypass` token (see pitfall #23) is required for any internal paths
3. **Idempotent writes?** If seeding rows, use `ON CONFLICT DO NOTHING` (Rule #5).
4. **`NOT NULL` columns?** If the target table has a `NOT NULL` column that isn't in your INSERT, the insert will silently fail — recall pitfall #20 (`unit_name NOT NULL` on `curriculum_units`).
5. **Downgrade path.** Write the inverse. If destructive (`DROP COLUMN` with data), call it out explicitly in the docstring.

## Step 4 — Prove the cycle (pitfall #27)

After writing, **do not commit until you've run**:

```bash
docker compose exec api alembic upgrade head
docker compose exec api alembic downgrade -1
docker compose exec api alembic upgrade head
```

All three must succeed. If the downgrade leaves orphan state (the L-1 debug draft bug fixed by migration 0048), rewrite the downgrade.

## Step 5 — Stage for review

Show me the file before anything else. **Do not auto-apply to any database beyond the local dev container.**

Remind me to update the migrations table in CLAUDE.md (the `| # | Description |` grid) — doc-drift check (Rule #16) catches code drift, not README drift.
