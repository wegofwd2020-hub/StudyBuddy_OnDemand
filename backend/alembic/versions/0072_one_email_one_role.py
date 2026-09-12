"""One email, one role — reject an address held by the other account table.

Decided 2026-09-12 after a tester found both of his student test accounts
logging in as staff. Each address existed as BOTH a `teachers` row and a
`students` row; `login_local_user` queries teachers first and falls through to
students only when nothing matched, so the student row was unreachable — no
error, no hint, just the wrong portal.

`teachers.email` and `students.email` have each been UNIQUE since 0001, so a
duplicate WITHIN a role was already impossible. What was missing is the
cross-table half: two constraints on two tables, neither aware of the other.

## Why a trigger and not an application check

There are 12 places that insert a teacher or a student — provisioning,
school self-registration, Auth0 exchange, roster upload, the dev router, two
demo services and the demo seeder. A guard in the provisioning endpoints would
have enforced the rule for the school-admin UI only, and every insert path
added later would opt out of it silently. A trigger is one implementation that
every path goes through, including paths that do not exist yet.

## Why not a shared identity table

That is the airtight answer — one table holding the email with a UNIQUE
constraint, referenced by both — and it has no race. A trigger's existence
check can be defeated by two concurrent inserts of the same new address into
different tables, because neither transaction can see the other's uncommitted
row. That window is narrow (two admins, same new address, same instant, two
different roles) and the failure is recoverable by hand, which is why the
cheaper enforcement was chosen deliberately rather than by omission. Filed as
a follow-up.

## Scoped to the LOCAL auth track

The rule is enforced only between `auth_provider='local'` rows, because that is
the only place the ambiguity exists: `login_local_user` resolves a person by
email with `auth_provider='local'`, teachers first and students second, so a
row on any other track is never returned by that lookup.

A broader rule would refuse a real flow — registering a school (local
school_admin) and then requesting a DEMO student account on the same address.
Demo rows live in `students` with `auth_provider='demo'`, the local lookup
skips them, and `/auth/universal-login` already resolves that precedence on
purpose. The first draft of this trigger blocked it and broke the test that
documents it, which is how the over-reach was caught.

## Deleted accounts are excluded, on purpose

ADR-005 makes account deletion a SOFT delete: the row is retained with
`account_status='deleted'` for FERPA record retention, and it keeps its email.
A guard that counted those rows would refuse an address permanently the first
time an account holding it was deleted — blocking a legitimate reuse rather
than the defect. So the check ignores deleted rows on the other side.

That exclusion has a consequence this migration does NOT own but which must
hold for it to be safe: once a live account may share an address with a DELETED
one, `login_local_user` must skip deleted rows when it falls through, or the
lookup lands on the dead row and refuses the login outright. Fixed in
`src/auth/service.py` in the same change.

## Errors surface as a unique violation, deliberately

`RAISE ... USING ERRCODE = 'unique_violation', CONSTRAINT = 'one_email_one_role'`
so asyncpg raises `UniqueViolationError` with a readable `constraint_name`. The
existing handlers already branch on `constraint_name` rather than on message
text (#578/#597) — this reuses that channel instead of introducing a second
kind of duplicate-email error for callers to learn about.

Comparison is case-insensitive (`lower()`). Every address on the demo is
already lowercase, and login matches case-SENSITIVELY, so a mixed-case variant
could otherwise slip past this guard and land in the unreachable state the
guard exists to prevent.

Revision ID: 0072
Revises: 0071
"""

from alembic import op

revision = "0072"
down_revision = "0071"
branch_labels = None
depends_on = None


# One function for both tables. `TG_ARGV[0]` names the table to search, so the
# rule reads identically from either side and cannot drift between two copies.
_FN = """
CREATE OR REPLACE FUNCTION enforce_one_email_one_role() RETURNS trigger AS $$
DECLARE
    other_table  text := TG_ARGV[0];
    other_role   text := TG_ARGV[1];
    clash        boolean;
BEGIN
    -- Nothing to check when the address is not changing (an UPDATE that
    -- touches other columns), or when it is absent.
    IF NEW.email IS NULL THEN
        RETURN NEW;
    END IF;
    IF TG_OP = 'UPDATE' AND OLD.email IS NOT DISTINCT FROM NEW.email THEN
        RETURN NEW;
    END IF;

    -- LOCAL accounts only, on both sides.
    --
    -- The ambiguity this exists to prevent lives entirely in the local login
    -- path: `login_local_user` looks a person up by email with
    -- `auth_provider = 'local'`, teachers first, students second. A row on any
    -- other track is never returned by that lookup and so can never shadow
    -- anything through it.
    --
    -- Blocking those rows too would condemn a flow that demonstrably works: a
    -- prospect who registers a school (local school_admin) and then requests a
    -- DEMO student account on the same address. `auth_provider='demo'`, the
    -- local lookup skips it, and `/auth/universal-login` already resolves the
    -- precedence deliberately — there is a test asserting exactly that. The
    -- first draft of this trigger broke it, which is how the over-reach was
    -- found.
    IF NEW.auth_provider IS DISTINCT FROM 'local' THEN
        RETURN NEW;
    END IF;

    -- Deleted accounts keep their address for FERPA retention (ADR-005) and
    -- must not reserve it forever.
    EXECUTE format(
        'SELECT EXISTS (SELECT 1 FROM %I WHERE lower(email) = lower($1)'
        '                AND auth_provider = ''local'''
        '                AND account_status <> ''deleted'')',
        other_table
    ) INTO clash USING NEW.email;

    IF clash THEN
        RAISE EXCEPTION
            'email % is already registered to a %', NEW.email, other_role
            USING ERRCODE = 'unique_violation',
                  CONSTRAINT = 'one_email_one_role';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""


def upgrade() -> None:
    op.execute(_FN)

    # BEFORE INSERT OR UPDATE OF email — narrowed to the column, so unrelated
    # updates (password resets, grade changes, status flips) do not pay for a
    # lookup they cannot invalidate.
    op.execute(
        """
        CREATE TRIGGER trg_teachers_one_email_one_role
        BEFORE INSERT OR UPDATE OF email ON teachers
        FOR EACH ROW EXECUTE FUNCTION enforce_one_email_one_role('students', 'student')
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_students_one_email_one_role
        BEFORE INSERT OR UPDATE OF email ON students
        FOR EACH ROW EXECUTE FUNCTION enforce_one_email_one_role('teachers', 'teacher')
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_students_one_email_one_role ON students")
    op.execute("DROP TRIGGER IF EXISTS trg_teachers_one_email_one_role ON teachers")
    op.execute("DROP FUNCTION IF EXISTS enforce_one_email_one_role()")
