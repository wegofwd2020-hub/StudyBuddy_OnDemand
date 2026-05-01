"""0052 — Per-school theme customization

Adds a nullable `theme` JSONB column to the `schools` table. The column stores
per-school accent colors and identity (name, logo URL). When NULL, clients fall
back to the default palette (amber/indigo/emerald/rose).

Schema shape:
  {
    "school": { "name": "...", "logoText": "...", "logoUrl": null },
    "subjects": {
      "Reading": { "accent": "#ea580c", "label": "Reading" },
      "Math":    { "accent": "#4f46e5", "label": "Math" },
      "Science": { "accent": "#059669", "label": "Science" },
      "World":   { "accent": "#e11d48", "label": "World" }
    }
  }

Revision ID: 0052
Revises: 0051
Create Date: 2026-05-01
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0052"
down_revision: str | None = "0051"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE schools ADD COLUMN IF NOT EXISTS theme JSONB;")


def downgrade() -> None:
    op.execute("ALTER TABLE schools DROP COLUMN IF EXISTS theme;")
