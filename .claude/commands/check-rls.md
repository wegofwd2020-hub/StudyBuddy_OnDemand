---
description: Audit RLS coverage across tenant-scoped tables; flag missing policies.
---

Read-only audit of Row-Level Security coverage. Makes no changes.

## Step 1 — List all tables with RLS enabled

```bash
grep -rE '^[[:space:]]*(ALTER TABLE|op\.execute).*ENABLE ROW LEVEL SECURITY' backend/alembic/versions/ | sort -u
```

Extract the table names. Baseline expected set (as of migration 0048):
- `schools`, `teachers`, `students`, `school_enrolments`, `student_teacher_assignments`, `curricula`, `content_subject_versions`, `classrooms`, `classroom_packages`, `classroom_students`, `curriculum_definitions`, `school_storage_quotas`, `grade_curriculum_assignments`, `school_llm_config`, `content_warning_acks`, plus any added after.

## Step 2 — For each table, verify there's a matching policy

For every table with `ENABLE ROW LEVEL SECURITY`, there must be at least one `CREATE POLICY`. Flag any table that has RLS enabled but no policy — this means **everyone is locked out**, which is rarely intended.

```bash
grep -rE '^[[:space:]]*(ALTER TABLE|op\.execute).*FORCE ROW LEVEL SECURITY' backend/alembic/versions/ | sort -u
grep -rE 'CREATE POLICY' backend/alembic/versions/ | sort -u
```

## Step 3 — Find tenant-scoped tables without RLS

Any table with a `school_id` column should have RLS unless it's intentionally global (e.g., `streams` registry).

```bash
grep -rE '^[[:space:]]*(sa\.Column.*school_id|ADD COLUMN.*school_id)' backend/alembic/versions/ | sort -u
```

Cross-reference against the RLS-enabled list from Step 1. Any table with `school_id` but no RLS is a finding.

## Step 4 — Spot-check the RESTRICTIVE write guards

Migration 0046 added per-command RESTRICTIVE policies on `curricula` that refuse INSERT/UPDATE/DELETE on `owner_type='platform'` rows from non-bypass sessions. Verify these still exist:

```bash
grep -E 'RESTRICTIVE|owner_type' backend/alembic/versions/0046*.py backend/alembic/versions/0048*.py
```

If a later migration dropped them without replacement, that's a finding.

## Step 5 — Report

Produce a table:

| Table | RLS enabled | FORCE | Policies found | Has school_id | Verdict |
|---|---|---|---|---|---|
| schools | ✓ | ✓ | 1 | self-scope | ok |
| ... | | | | | |

Verdict options: **ok**, **missing policy**, **missing RLS on tenant table**, **unusual — investigate**.

## Step 6 — Remind about test coverage

If any finding, before proposing a fix: **RLS tests must run as `studybuddy_rls_tester`** (a non-superuser role). The `studybuddy` role is a superuser and bypasses `FORCE ROW LEVEL SECURITY` — tests running as that role give false positives. See the project memory `feedback_test_rls_superuser.md`.

## Step 7 — DO NOT auto-fix

Report findings. Wait for me to say which ones to address. RLS changes are migration changes, so fixes go through `/new-migration`.
