#!/usr/bin/env python3
"""
backend/scripts/export_openapi.py

Export the FastAPI OpenAPI schema to stdout (or a file) without starting
a live server.  Used in CI to generate TypeScript types from the schema.

Usage:
    # Inside the api container:
    python scripts/export_openapi.py > ../web/openapi.json

    # Or from the repo root (requires Python env with backend deps installed):
    cd backend && python scripts/export_openapi.py > ../web/openapi.json

    # Write to a specific file:
    python scripts/export_openapi.py --out path/to/openapi.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys

# Allow running from repo root or from backend/.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Stub out missing required env vars so the Settings object can be imported
# without a .env file (CI doesn't have one).  Values are never used because
# we only call app.openapi() — no DB/Redis connections are opened.
_STUBS = {
    # Force production mode so the dev router (/auth/dev-login) is never
    # included in the exported schema.  APP_ENV defaults to "development"
    # in config.py which would cause schema drift between local and CI.
    "APP_ENV": "production",
    "DATABASE_URL": "postgresql://stub:stub@localhost/stub",
    "REDIS_URL": "redis://localhost:6379/0",
    "JWT_SECRET": "stub-jwt-secret-min-32-chars-aaaabbbb",
    "ADMIN_JWT_SECRET": "stub-admin-secret-min-32-chars-ccccdddd",
    "AUTH0_DOMAIN": "stub.auth0.com",
    "AUTH0_JWKS_URL": "https://stub.auth0.com/.well-known/jwks.json",
    "AUTH0_STUDENT_CLIENT_ID": "stub-student-client",
    "AUTH0_TEACHER_CLIENT_ID": "stub-teacher-client",
    "AUTH0_MGMT_CLIENT_ID": "stub-mgmt-client",
    "AUTH0_MGMT_CLIENT_SECRET": "stub-mgmt-secret-aaaaaaaaaaa",
    "AUTH0_MGMT_API_URL": "https://stub.auth0.com/api/v2",
    "METRICS_TOKEN": "stub-metrics-token",
}
for key, val in _STUBS.items():
    os.environ.setdefault(key, val)

from main import app  # noqa: E402  (import after env stubs)


def main() -> None:
    parser = argparse.ArgumentParser(description="Export FastAPI OpenAPI schema to JSON")
    parser.add_argument(
        "--out",
        metavar="FILE",
        help="Write output to FILE instead of stdout",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        metavar="N",
        help="JSON indent level (default: 2)",
    )
    args = parser.parse_args()

    schema = app.openapi()
    output = json.dumps(schema, indent=args.indent)

    if args.out:
        with open(args.out, "w") as fh:
            fh.write(output)
            fh.write("\n")
        print(f"Wrote {len(schema['paths'])} paths to {args.out}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
