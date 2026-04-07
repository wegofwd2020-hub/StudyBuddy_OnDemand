#!/usr/bin/env bash
# =============================================================================
# StudyBuddy OnDemand — Local Host PostgreSQL Init
#
# PURPOSE
#   Creates the studybuddy role and databases on the host PostgreSQL instance
#   (expected on port 5433) so Docker containers can connect to it via
#   host.docker.internal:5433.
#
#   Run this once per machine. Safe to re-run — all CREATE statements use
#   IF NOT EXISTS / ON CONFLICT guards.
#
# PREREQUISITES
#   • PostgreSQL running on the host at port 5433 and accepting TCP connections
#     (Ubuntu: systemctl status postgresql)
#   • PostgreSQL superuser (postgres) password to hand
#   • sudo access (needed to edit pg_hba.conf for Docker bridge access)
#
# USAGE
#   chmod +x scripts/local-db-init.sh
#   ./scripts/local-db-init.sh
#
# The script will prompt for:
#   1. The postgres superuser password (for all DDL operations)
#   2. The password to set for the new 'studybuddy' role
#
# AFTER RUNNING
#   1. Set LOCAL_DB_PASSWORD=<chosen-password> in your .env.local
#   2. Start stack: docker compose -f docker-compose.yml -f docker-compose.local.yml up
#      Migrations run automatically on first up via the migrate service.
#
# TO REINITIALIZE (wipe and start fresh)
#   PGPASSWORD=<postgres-password> psql -h localhost -p 5433 -U postgres \
#     -c "DROP DATABASE studybuddy;" \
#     -c "DROP DATABASE studybuddy_test;"
#   Then re-run this script.
# =============================================================================

set -euo pipefail

PG_HOST=localhost
PG_PORT=5433
PG_SUPERUSER=postgres
DOCKER_BRIDGE_CIDR="172.16.0.0/12"

# ── Prompt for passwords ─────────────────────────────────────────────────────
echo ""
echo "StudyBuddy — Host PostgreSQL initializer"
echo "Port: ${PG_PORT}  Superuser: ${PG_SUPERUSER}"
echo ""
read -r -s -p "Enter password for the '${PG_SUPERUSER}' superuser: " PG_SUPERUSER_PASSWORD
echo ""

if [[ -z "${PG_SUPERUSER_PASSWORD}" ]]; then
    echo "ERROR: Superuser password cannot be empty." >&2
    exit 1
fi

read -r -s -p "Enter password to set for the 'studybuddy' role: " SB_PASSWORD
echo ""
read -r -s -p "Confirm password: " SB_PASSWORD_CONFIRM
echo ""

if [[ "${SB_PASSWORD}" != "${SB_PASSWORD_CONFIRM}" ]]; then
    echo "ERROR: Passwords do not match." >&2
    exit 1
fi

if [[ -z "${SB_PASSWORD}" ]]; then
    echo "ERROR: Password cannot be empty." >&2
    exit 1
fi

# ── Helper: run SQL as postgres superuser ────────────────────────────────────
run_sql() {
    PGPASSWORD="${PG_SUPERUSER_PASSWORD}" psql -h "${PG_HOST}" -p "${PG_PORT}" -U "${PG_SUPERUSER}" -v ON_ERROR_STOP=1 -c "$1"
}

run_sql_db() {
    local db=$1; shift
    PGPASSWORD="${PG_SUPERUSER_PASSWORD}" psql -h "${PG_HOST}" -p "${PG_PORT}" -U "${PG_SUPERUSER}" -d "${db}" -v ON_ERROR_STOP=1 -c "$1"
}

echo ""
echo "── Step 1: Create 'studybuddy' role ─────────────────────────────────────"
run_sql "
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'studybuddy') THEN
        CREATE ROLE studybuddy WITH LOGIN PASSWORD '${SB_PASSWORD}';
        RAISE NOTICE 'Role studybuddy created.';
    ELSE
        ALTER ROLE studybuddy WITH PASSWORD '${SB_PASSWORD}';
        RAISE NOTICE 'Role studybuddy already exists — password updated.';
    END IF;
END
\$\$;
"

echo ""
echo "── Step 2: Create development database ──────────────────────────────────"
if PGPASSWORD="${PG_SUPERUSER_PASSWORD}" psql -h "${PG_HOST}" -p "${PG_PORT}" -U "${PG_SUPERUSER}" -lqt | cut -d '|' -f1 | grep -qw studybuddy; then
    echo "  Database 'studybuddy' already exists — skipping."
else
    run_sql "CREATE DATABASE studybuddy OWNER studybuddy;"
    echo "  Database 'studybuddy' created."
fi

echo ""
echo "── Step 3: Create test database ─────────────────────────────────────────"
if PGPASSWORD="${PG_SUPERUSER_PASSWORD}" psql -h "${PG_HOST}" -p "${PG_PORT}" -U "${PG_SUPERUSER}" -lqt | cut -d '|' -f1 | grep -qw studybuddy_test; then
    echo "  Database 'studybuddy_test' already exists — skipping."
else
    run_sql "CREATE DATABASE studybuddy_test OWNER studybuddy;"
    echo "  Database 'studybuddy_test' created."
fi

echo ""
echo "── Step 4: Grant privileges ──────────────────────────────────────────────"
run_sql_db "studybuddy" "
GRANT ALL PRIVILEGES ON DATABASE studybuddy TO studybuddy;
GRANT ALL ON SCHEMA public TO studybuddy;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO studybuddy;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO studybuddy;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO studybuddy;
"
run_sql_db "studybuddy_test" "
GRANT ALL PRIVILEGES ON DATABASE studybuddy_test TO studybuddy;
GRANT ALL ON SCHEMA public TO studybuddy;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO studybuddy;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO studybuddy;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO studybuddy;
"
echo "  Privileges granted."

echo ""
echo "── Step 5: pg_hba.conf — Docker bridge access ───────────────────────────"
# Find the PostgreSQL data directory
HBA_FILE=$(PGPASSWORD="${PG_SUPERUSER_PASSWORD}" psql -h "${PG_HOST}" -p "${PG_PORT}" -U "${PG_SUPERUSER}" -t -c "SHOW hba_file;" 2>/dev/null | xargs || true)

if [[ -z "${HBA_FILE}" ]]; then
    echo "  WARNING: Could not determine pg_hba.conf location automatically."
    echo "  Manually add this line to your pg_hba.conf:"
    echo ""
    echo "    host  all  studybuddy  ${DOCKER_BRIDGE_CIDR}  scram-sha-256"
    echo ""
else
    BRIDGE_RULE="host    all             studybuddy      ${DOCKER_BRIDGE_CIDR}         scram-sha-256"
    if grep -qF "${DOCKER_BRIDGE_CIDR}" "${HBA_FILE}" 2>/dev/null; then
        echo "  Docker bridge rule already present in ${HBA_FILE} — skipping."
    else
        echo "  Adding Docker bridge rule to ${HBA_FILE} ..."
        if [[ -w "${HBA_FILE}" ]]; then
            # Append before the last line (typically a comment or catch-all)
            echo "${BRIDGE_RULE}" >> "${HBA_FILE}"
            echo "  Added: ${BRIDGE_RULE}"
        else
            echo "  File not writable directly. Attempting sudo ..."
            echo "${BRIDGE_RULE}" | sudo tee -a "${HBA_FILE}" > /dev/null
            echo "  Added via sudo: ${BRIDGE_RULE}"
        fi
        echo "  Reloading PostgreSQL config ..."
        run_sql "SELECT pg_reload_conf();" > /dev/null
        echo "  PostgreSQL config reloaded."
    fi
fi

echo ""
echo "── Step 6: Verify connection from host ──────────────────────────────────"
if PGPASSWORD="${SB_PASSWORD}" psql -h "${PG_HOST}" -p "${PG_PORT}" -U studybuddy -d studybuddy -c "SELECT 1;" > /dev/null 2>&1; then
    echo "  OK — studybuddy role can connect to studybuddy database."
else
    echo "  WARNING: Connection test failed. Check pg_hba.conf and PostgreSQL logs."
fi

# ── Done ─────────────────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════════════════════════"
echo "  Setup complete."
echo ""
echo "  Next steps:"
echo ""
echo "  1. Add to your .env.local (in the project root):"
echo "       LOCAL_DB_PASSWORD=${SB_PASSWORD}"
echo "       SB_API_PORT=8010   # change if 8000 is taken by another project"
echo "       SB_WEB_PORT=3010   # change if 3000 is taken by another project"
echo ""
echo "  2. Start the stack:"
echo "       docker compose -f docker-compose.yml -f docker-compose.local.yml up"
echo ""
echo "  3. To run migrations manually (if needed):"
echo "       docker compose -f docker-compose.yml -f docker-compose.local.yml \\"
echo "           run --rm migrate alembic upgrade head"
echo ""
echo "  4. To reinitialize the DB schema (destructive — dev only):"
echo "       PGPASSWORD='${SB_PASSWORD}' psql -p ${PG_PORT} -U studybuddy \\"
echo "           -c 'DROP SCHEMA public CASCADE; CREATE SCHEMA public;' studybuddy"
echo "       Then re-run migrations."
echo "═══════════════════════════════════════════════════════════════════════════"
