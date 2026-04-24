"""
backend/src/core/cors.py

CORS helpers for local-dev and pre-edge deploys.

Production CORS is expected to be handled at the edge (Cloudflare + future
API gateway). This module exists for two interim states where that edge is
not yet in front of the service:

1. Local dev — `uvicorn` loaded from localhost or a LAN peer (e.g.
   192.168.x.x) during a customer demo, with the Next.js dev server on
   port 3000/3010.
2. Pre-edge cloud deploys — service on a public VM under a real hostname
   before the edge layer lands. Cloud origins are exact-match entries in
   ALLOWED_ORIGINS / CORS_EXTRA_ORIGINS.

With Option B's same-origin rewrites() proxy the browser talks to the
Next.js origin only, so the LAN regex is mostly defense in depth —
direct browser-to-backend hits still need a sane allowlist.
"""

from __future__ import annotations

# Allowed LAN web ports — mirrors docker-compose (3000 primary, 3010 admin).
_WEB_PORTS: tuple[int, ...] = (3000, 3010)

# RFC-1918 + loopback host patterns. Matches localhost, IPv4/IPv6 loopback,
# and all three RFC-1918 private ranges.
_HOST_PATTERNS: tuple[str, ...] = (
    r"localhost",
    r"\[::1\]",  # IPv6 loopback, bracketed in URLs
    r"127(?:\.\d{1,3}){3}",  # 127.0.0.0/8
    r"10(?:\.\d{1,3}){3}",  # 10.0.0.0/8
    r"172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2}",  # 172.16.0.0/12
    r"192\.168(?:\.\d{1,3}){2}",  # 192.168.0.0/16
)


def build_lan_origin_regex() -> str:
    """Regex for CORSMiddleware(allow_origin_regex=...).

    Admits http://<loopback-or-RFC1918>:<web-port>. HTTPS is excluded —
    LAN demos run plain HTTP; cloud origins go through the exact-match
    allowlist (ALLOWED_ORIGINS / CORS_EXTRA_ORIGINS).
    """
    hosts = "|".join(_HOST_PATTERNS)
    ports = "|".join(str(p) for p in _WEB_PORTS)
    return rf"^http://(?:{hosts}):(?:{ports})$"


def parse_extra_origins(env_value: str | None) -> list[str]:
    """Parse comma-separated CORS_EXTRA_ORIGINS → list of exact origins.

    Empty entries and surrounding whitespace are stripped. Empty input
    returns an empty list.
    """
    if not env_value:
        return []
    return [o.strip() for o in env_value.split(",") if o.strip()]
