"""
backend/src/utils/logger.py

Structured JSON logger using structlog + stdlib logging.
All backend components import get_logger() from here.
Never use print(); never log passwords, JWT tokens, or Stripe keys.
"""

from __future__ import annotations

import logging
import sys

import structlog


def _configure_structlog() -> None:
    """Configure structlog once at import time."""
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    structlog.configure(
        processors=shared_processors
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.processors.JSONRenderer(),
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    # Only add handler if not already configured (avoid duplicate handlers in tests).
    if not root_logger.handlers:
        root_logger.addHandler(handler)


_configure_structlog()


def get_logger(component: str) -> structlog.stdlib.BoundLogger:
    """
    Return a bound structlog logger for the given component.

    Usage:
        log = get_logger("auth")
        log.info("token_issued", student_id=str(student_id))
    """
    return structlog.get_logger(component)
