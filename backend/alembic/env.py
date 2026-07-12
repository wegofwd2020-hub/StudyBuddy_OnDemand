"""
alembic/env.py

Alembic migration environment.

Uses DATABASE_URL from config.py (via pydantic-settings / .env file).
Runs in non-async mode using psycopg2 (synchronous) for Alembic compatibility;
the application itself uses asyncpg at runtime.
"""

from __future__ import annotations

import os
import sys

# Ensure the backend package is importable when running alembic from backend/.
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from alembic import context

# Pull DATABASE_URL from our settings (reads .env automatically).
# TEST_DB_URL takes precedence when running the test suite so migrations
# target studybuddy_test instead of the dev database.
from config import settings
from sqlalchemy import engine_from_config, pool

_test_db_url = os.environ.get("TEST_DB_URL")
_raw_url = _test_db_url or settings.DATABASE_URL
# Strip +asyncpg driver suffix if present — alembic uses psycopg2.
_db_url = _raw_url.replace("+asyncpg", "").replace("postgresql://", "postgresql+psycopg2://")
if not _db_url.startswith("postgresql"):
    _db_url = _raw_url

# Announce the target database, loudly, every time.
#
# TEST_DB_URL is set on the `api` service, so `docker compose exec api alembic
# upgrade head` — the command the docs give for a manual migration — silently
# migrates studybuddy_test and reports success while the dev database stays
# behind. (`docker-compose.yml` blanks TEST_DB_URL for the `migrate` service for
# exactly this reason, but nothing protects an interactive exec.) The failure
# mode is pitfall #18 — UndefinedColumnError *after* you ran the migration.
#
# Rather than change the precedence, which the test harness depends on, say which
# database is about to be touched so a wrong target is obvious rather than silent.
_target_db = _db_url.rsplit("/", 1)[-1].split("?")[0]
if _test_db_url:
    print(
        f"alembic: targeting TEST database '{_target_db}' (TEST_DB_URL is set).\n"
        f"         To migrate the dev database instead, unset it:\n"
        f"         docker compose exec -e TEST_DB_URL= api alembic upgrade head",
        file=sys.stderr,
    )
else:
    print(f"alembic: targeting database '{_target_db}'", file=sys.stderr)

config = context.config
config.set_main_option("sqlalchemy.url", _db_url)

# No SQLAlchemy metadata object — we write raw DDL in migration scripts.
target_metadata = None


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (no DB connection required)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (requires live DB connection)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
