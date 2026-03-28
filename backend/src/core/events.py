"""
backend/src/core/events.py

Application event emission and audit log dispatch.

emit_event()     — structured log entry + Prometheus counter increment
write_audit_log() — dispatches a Celery task to insert an audit_log row
                    (fire-and-forget; never blocks the request path)
"""

from __future__ import annotations

import uuid
from typing import Any

from src.core.observability import correlation_id_var, events_total
from src.utils.logger import get_logger

log = get_logger("events")


def emit_event(
    category: str,
    event_type: str,
    **ctx: Any,
) -> None:
    """
    Emit a structured application event.

    Increments the sb_events_total counter and writes a structured log entry.
    This is synchronous (no I/O) and safe to call from async handlers.

    Args:
        category:   broad grouping, e.g. "auth", "content", "subscription"
        event_type: specific event, e.g. "token_issued", "lesson_served"
        **ctx:      additional key/value context included in the log entry
    """
    events_total.labels(category=category, event_type=event_type).inc()
    log.info(
        event_type,
        category=category,
        correlation_id=correlation_id_var.get(),
        **ctx,
    )


def write_audit_log(
    event_type: str,
    actor_type: str,
    actor_id: uuid.UUID | None,
    target_type: str | None = None,
    target_id: uuid.UUID | None = None,
    metadata: dict | None = None,
    ip_address: str | None = None,
) -> None:
    """
    Dispatch a Celery task to write an audit_log row.

    This is fire-and-forget: the Celery task runs asynchronously and is
    never awaited on the request path.  The task is defined in
    src/auth/tasks.py.

    Import is deferred to avoid circular imports at module load time.
    """
    try:
        from src.auth.tasks import write_audit_log_task

        write_audit_log_task.delay(
            event_type=event_type,
            actor_type=actor_type,
            actor_id=str(actor_id) if actor_id else None,
            target_type=target_type,
            target_id=str(target_id) if target_id else None,
            metadata=metadata,
            ip_address=ip_address,
            correlation_id=correlation_id_var.get(),
        )
    except Exception as exc:
        # Audit log failure must never break a user-facing request.
        log.error("audit_log_dispatch_failed", error=str(exc))
