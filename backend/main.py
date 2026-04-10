"""
backend/main.py

FastAPI application entry point.

All app construction lives in src/core/app_factory.py:
  - Lifespan (asyncpg + aioredis pool create/close)
  - Middleware (CorrelationId, CORS)
  - Exception handlers (HTTP, unhandled, rate-limit)
  - Router registration (/api/v1/* + health/metrics)

Workers:
  gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker
  uvicorn main:app --reload  (development)
"""

from src.core.app_factory import create_app

app = create_app()
