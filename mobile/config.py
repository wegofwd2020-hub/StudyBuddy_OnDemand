"""
mobile/config.py

Mobile app configuration — no secrets.

All sensitive keys (Anthropic, Stripe) are absent from mobile.
The mobile app only needs to know where the backend is.
Auth0 client_id is a public value (safe to embed in mobile apps).
"""

import os

# ── App version ───────────────────────────────────────────────────────────────
# Sent as X-App-Version on every backend request.
# The backend enforces a minimum supported version (MINIMUM_SUPPORTED_APP_VERSION
# in backend/config.py) and returns 426 Upgrade Required when this is too old.
APP_VERSION = "2.0.0"

# ── Backend connection ─────────────────────────────────────────────────────────
BACKEND_URL = os.getenv("STUDYBUDDY_BACKEND_URL", "http://localhost:8000")

# ── Auth0 public config ────────────────────────────────────────────────────────
# These values are not secrets — client IDs are public in PKCE flows.
AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN", "your-tenant.auth0.com")
AUTH0_CLIENT_ID = os.getenv("AUTH0_CLIENT_ID", "your-auth0-student-app-client-id")
AUTH0_REDIRECT_URI = "studybuddy://callback"

# ── Local storage ──────────────────────────────────────────────────────────────
# SQLITE_DB_PATH is set at runtime from App.user_data_dir (set by Kivy).
SQLITE_DB_PATH: str | None = None
JWT_STORAGE_FILENAME = "jwt.token"
REFRESH_TOKEN_FILENAME = "refresh.token"

# ── Cache limits ───────────────────────────────────────────────────────────────
MAX_CACHE_MB = 200

# ── Offline sync ──────────────────────────────────────────────────────────────
SYNC_RETRY_INTERVAL_SECONDS = 30
MAX_QUEUE_SIZE = 1000
