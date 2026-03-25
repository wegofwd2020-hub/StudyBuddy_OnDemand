"""
alembic/env.py

Alembic migration environment.

Uses DATABASE_URL from config.py (via pydantic-settings / .env file).
Runs in non-async mode using psycopg2 (synchronous) for Alembic compatibility;
the application itself uses asyncpg at runtime.
"""

from __future__ import annotations

import sys
import os

# Ensure the backend package is importable when running alembic from backend/.
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from alembic import context
from sqlalchemy import engine_from_config, pool

# Pull DATABASE_URL from our settings (reads .env automatically).
from config import settings

# Strip +asyncpg driver suffix if present — alembic uses psycopg2.
_db_url = settings.DATABASE_URL.replace("+asyncpg", "").replace("postgresql://", "postgresql+psycopg2://")
if not _db_url.startswith("postgresql"):
    _db_url = settings.DATABASE_URL

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
