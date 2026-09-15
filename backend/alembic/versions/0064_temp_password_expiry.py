"""0064 — give school-issued temporary passwords an expiry.

Issue #664, reported by Venki 2026-08-27: a password emailed the previous day
still logged him in. Provisioning generates a random password, emails it in
plaintext, and sets `first_login = TRUE` — but nothing bounds how long that
credential stays valid.

So a temporary password sits in an inbox, and in every mail archive, forward and
backup it reaches, and works indefinitely. `first_login` is a PROMPT, not an
expiry: it fires whenever the person eventually logs in, which may be never,
while the password stays live.

`password_expires_at` is stamped when a TEMPORARY password is issued
(provisioning and admin reset) and cleared when the user sets their own. A
user's chosen password never expires — only the one somebody else picked and
sent them.

## NULL means "no expiry", deliberately

Every existing row backfills to NULL rather than to a date. Stamping the
existing rows would lock out every already-provisioned account whose owner has
not logged in yet — including, on the demo, accounts the tester is mid-way
through using. The bound applies to credentials issued from here on; the
already-issued ones stay reachable and are covered by rotating them, not by a
migration.

Revision ID: 0064
Revises: 0063
"""

from alembic import op

revision = "0064"
down_revision = "0063"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table in ("teachers", "students"):
        op.execute(f"""
            ALTER TABLE {table}
            ADD COLUMN IF NOT EXISTS password_expires_at TIMESTAMPTZ
        """)
        op.execute(f"""
            COMMENT ON COLUMN {table}.password_expires_at IS
            'When a school-issued TEMPORARY password stops being accepted. '
            'NULL means no expiry: either the user chose this password '
            'themselves, or it predates issue #664.'
        """)


def downgrade() -> None:
    for table in ("teachers", "students"):
        op.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS password_expires_at")
