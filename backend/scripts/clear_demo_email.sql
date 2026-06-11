-- clear_demo_email.sql
--
-- Free up a demo email address so it can be re-used to sign up for a new
-- demo (student or teacher) account.
--
-- Why this is needed: the demo signup flow creates a `students` (or `teachers`)
-- row carrying the email, and `students.email` / `teachers.email` are UNIQUE
-- (migration 0001). Re-requests are also blocked with HTTP 409 by an active
-- `demo_accounts` row and/or a `pending` `demo_requests` + unused verification
-- (see backend/src/demo/router.py + service.py; same for the teacher tables).
-- Clearing all of these for the address makes it immediately reusable.
--
-- Note: `students` / `teachers` have FORCE row-level security (migration 0028),
-- so this script sets the `bypass` sentinel on app.current_school_id. Connect as
-- the app role (studybuddy) or a superuser — both work with the bypass set.
--
-- Usage:
--   Inspect only (dry run — shows what WOULD be removed, deletes nothing):
--     psql "$DATABASE_URL" -v email=callmds@gmail.com -f backend/scripts/clear_demo_email.sql
--
--   Actually delete (add -v confirm=yes):
--     psql "$DATABASE_URL" -v email=callmds@gmail.com -v confirm=yes -f backend/scripts/clear_demo_email.sql
--
-- Safety: the `students` / `teachers` deletes are guarded by auth_provider='demo'
-- so a real Auth0 / local-auth account sharing the address is never touched.

\set ON_ERROR_STOP on

-- ── require -v email=... ────────────────────────────────────────────────────
\if :{?email}
\else
  \echo '*** ERROR: missing email. Pass  -v email=address@example.com'
  \quit
\endif

-- ── default confirm=no unless caller passed -v confirm=yes ──────────────────
\if :{?confirm}
\else
  \set confirm no
\endif

SET app.current_school_id = 'bypass';

\echo ''
\echo '== Rows currently matching' :'email' '=='

SELECT 'students'              AS table_name, student_id::text AS id, email, auth_provider AS detail
  FROM students               WHERE email = :'email'
UNION ALL
SELECT 'teachers',              teacher_id::text, email, auth_provider
  FROM teachers                WHERE email = :'email'
UNION ALL
SELECT 'demo_requests',         id::text, email, status
  FROM demo_requests           WHERE email = :'email'
UNION ALL
SELECT 'demo_accounts',         id::text, email, COALESCE(revoked_at::text, 'active')
  FROM demo_accounts           WHERE email = :'email'
UNION ALL
SELECT 'demo_teacher_requests', id::text, email, status
  FROM demo_teacher_requests   WHERE email = :'email'
UNION ALL
SELECT 'demo_teacher_accounts', id::text, email, ''
  FROM demo_teacher_accounts   WHERE email = :'email'
UNION ALL
SELECT 'demo_leads',            id::text, email, status
  FROM demo_leads              WHERE email = :'email'
ORDER BY table_name;

\if :confirm
  \echo ''
  \echo '== Deleting (confirm=yes) =='

  BEGIN;
    SET LOCAL app.current_school_id = 'bypass';

    -- Demo identity rows. The auth_provider='demo' guard protects real accounts.
    -- Cascades remove demo_accounts / demo_teacher_accounts and that user's
    -- progress / sessions automatically (ON DELETE CASCADE).
    DELETE FROM students WHERE email = :'email' AND auth_provider = 'demo';
    DELETE FROM teachers WHERE email = :'email' AND auth_provider = 'demo';

    -- Request rows (cascade to verifications + any leftover demo accounts).
    DELETE FROM demo_requests         WHERE email = :'email';
    DELETE FROM demo_teacher_requests WHERE email = :'email';

    -- Marketing "request a demo" lead-gen rows, if the address used that form.
    DELETE FROM demo_leads WHERE email = :'email';
  COMMIT;

  \echo ''
  \echo '== Done. Address is now reusable. =='
\else
  \echo ''
  \echo '== DRY RUN — nothing deleted. Re-run with  -v confirm=yes  to delete. =='
\endif
