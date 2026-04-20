---
description: Add a new FastAPI endpoint end-to-end — spec → schema → service → router → audit → test.
---

You are adding a new endpoint in module: **$ARGUMENTS**

## Gate 0 — Spec first

Before any code, invoke `/spec-first <same feature>` and wait for approval on the spec. Do NOT skip this. The rest of this command assumes the spec is approved.

If `$ARGUMENTS` is ambiguous about the module (e.g., "add an invite endpoint"), ask me which `backend/src/<module>/` it belongs in. Look at the existing modules:
```bash
ls backend/src/ | grep -v __pycache__
```

## Implementation order

Once the spec is approved, implement in this order — do not skip steps:

### 1. Migration (only if schema changes)

Run `/new-migration <slug>`. Complete the full downgrade→upgrade cycle (pitfall #27) before moving on.

### 2. Schema (pydantic)

Add request/response models to `backend/src/<module>/schemas.py`. Rules:
- Money fields → `condecimal(max_digits=14, decimal_places=2)` (Rule #1). Never `float`.
- UUIDs → `UUID` type. Dates → `datetime` with explicit tz.
- Validators on any field that has a business rule (length, range, regex).

### 3. Service layer

Business logic in `backend/src/<module>/service.py`. Rules:
- Async throughout. No blocking calls on the event loop (pitfall #2).
- `bcrypt` and CPU work → `asyncio.run_in_executor`.
- Emit structured events via `emit_event()` at decision points.
- Fire-and-forget writes (progress / analytics / audit) via Celery — don't await on the request path (pitfall #4).

### 4. Router

HTTP glue in `backend/src/<module>/router.py`. Rules:
- Path under `/api/v1/`.
- Auth dependency matches the persona track from the spec (one of: `require_student`, `require_teacher`, `require_school_admin`, `require_admin`). Mixing tracks is pitfall #13.
- `get_db` for tenant-scoped paths (stamps `app.current_school_id`). For paths that must bypass RLS (login lookup), see pitfall #23 and use the explicit bypass pattern.
- Rate-limit decorator if specified in the spec.

### 5. Audit (if writing)

For any state-changing operation on auth, finance, admin, or impersonation surfaces (Rule #7): call `write_audit_log()` with `{actor_id, action, target_type, target_id, old_state, new_state}`. Fire-and-forget via Celery.

### 6. Tests

Add to `backend/tests/<module>/`. Rules:
- `pytest` + `httpx.AsyncClient`. `fakeredis` for Redis. Mock Stripe / Anthropic / Auth0 at module level.
- Use the `studybuddy_test` DB from `TEST_DB_URL` — session-scoped fixture rolls back per test.
- RLS assertions MUST use the `studybuddy_rls_tester` non-superuser role — `studybuddy` bypasses `FORCE ROW LEVEL SECURITY`.
- Deterministic UUIDs + fixed timestamps in assertions (Rule #9).

### 7. OpenAPI + types

Run `/regen-openapi`. If `web/lib/api/types.gen.ts` diffs, stage it in the same commit as the router change — contract drift detected in CI is harder to debug than contract drift detected locally.

### 8. Docs

If this endpoint is user-facing or admin-visible, update the relevant route map in CLAUDE.md.

## Before declaring done

Invoke `/done` (when it exists) or run the equivalent gate by hand: backend `pytest` + `ruff` + `bandit`; web `npm test` + `lint` + `typecheck`; `alembic check`; OpenAPI regen shows no unexpected drift.
