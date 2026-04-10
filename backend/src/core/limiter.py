"""
backend/src/core/limiter.py

Shared slowapi Limiter instance used by auth routers.

The same limiter must be assigned to app.state.limiter in main.py so that
slowapi can locate it at request time.  State is in-process (per worker); for
stricter cross-worker enforcement, a load-balancer layer (nginx, AWS ALB) or
Redis-backed storage should be configured in production.

Rate limits applied:
  - Auth token-exchange endpoints:  10 req/min per IP
  - Forgot-password (IP layer):     10 req/min per IP
  - Admin login / password reset:   10 req/min per IP
  - Forgot-password (email layer):  5 req/hour per email (Redis, in-router)
"""
from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
