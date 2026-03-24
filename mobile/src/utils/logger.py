"""
mobile/src/utils/logger.py

Structured JSON logger for the mobile app — same pattern as backend.

Uses structlog for consistent JSON output.  Logs go to stdout, which is
captured by the Android/iOS system log or redirected by the operator.

Usage:
    from mobile.src.utils.logger import get_logger
    log = get_logger("auth")
    log.info("token_loaded", filename="jwt.token")

Never use print(). Never log JWT tokens, passwords, or other secrets.
"""

from __future__ import annotations

import logging
import sys

import structlog


def _configure() -> None:
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    structlog.configure(
        processors=shared_processors + [
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

    root = logging.getLogger()
    if not root.handlers:
        root.addHandler(handler)
    root.setLevel(logging.INFO)


_configure()


def get_logger(component: str) -> structlog.stdlib.BoundLogger:
    """Return a bound structlog logger for a given component."""
    return structlog.get_logger(component)
