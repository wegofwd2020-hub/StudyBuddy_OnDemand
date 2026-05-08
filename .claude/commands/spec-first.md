---
description: Draft a spec (tests + contract + acceptance) BEFORE implementation. Stop and wait for approval.
---

You are starting work on:

**Feature / change:** $ARGUMENTS

Before writing any implementation code, draft a spec covering the four sections below. After showing me the spec, **stop and wait for my approval** — do not touch any source file until I say "approved" (or ask for revisions).

---

## 1. Failing test(s)

Write the test(s) that would pass once this is correctly implemented. Be concrete — real function names, real assertions, the smallest set that proves correctness. Show them as code blocks; don't run them yet (they should fail because the feature doesn't exist).

Pick the stack that matches the layer:

| Layer | Stack |
|---|---|
| Backend logic / endpoints | `pytest` + `httpx.AsyncClient` |
| Web components / hooks | vitest + `@testing-library/react` |
| Cross-persona flows | Playwright in `web/tests/e2e/` (run from host — see pitfall #26) |
| Pipeline | `pytest` with mocked Anthropic + TTS SDKs |

## 2. API contract (only if adding or changing an endpoint)

- HTTP method + path — scoped under `/api/v1/`
- Auth track — one of: Auth0-student / Auth0-teacher / local (school-provisioned) / admin-bcrypt
- Request schema — pydantic model with field types and validators
- Response schema — success shape + HTTP status
- Error cases — enumerate from {400, 401, 403, 404, 409, 422, 429} with the condition that triggers each
- **Idempotency key** — does this POST/PATCH accept `Idempotency-Key`? Dedup strategy (e.g., `stripe_events` pattern)?
- **Rate limit** — target (e.g., 100/min per JWT, 10/min per IP for auth). Which bucket?
- **RLS scope** — is the path under `get_db()` (tenant-stamped via `app.current_school_id`), a bypass context (e.g., login — see pitfall #23), or admin (bypass)?
- **Observability** — which `emit_event` calls fire, which audit rows `write_audit_log` writes, which `/metrics` counter/histogram moves

## 3. Data / migration impact (only if schema changes)

- New tables / columns / indexes
- RLS policy changes — FORCE vs PERMISSIVE vs RESTRICTIVE, per-command or all-command
- Next sequential migration number in `backend/alembic/versions/`
- Downgrade path — is it safe? Does it destroy data? Any data-only rows to drop first?
- Backfill strategy if altering an existing column with `NOT NULL` or new default
- Rule #16 doc-drift: any docstring/README mentioning a renamed identifier?

## 4. Acceptance criteria checklist

Copy-paste-ready checklist to run against the PR:

- [ ] Test(s) from §1 pass
<!-- doc-audit:ignore -->
- [ ] Contract from §2 matches the implementation (`scripts/export_openapi.py` + `npm run gen:types` show no unexpected drift)
- [ ] Migration applies cleanly on a fresh DB **and** downgrades cleanly — run full downgrade→upgrade cycle (pitfall #27)
- [ ] RLS behaviour verified with the `studybuddy_rls_tester` non-superuser role — `studybuddy` bypasses `FORCE ROW LEVEL SECURITY`
- [ ] Observability visible — `/metrics` exposes the new counter, audit row present, correlation ID propagates through logs
- [ ] CLAUDE.md top pitfalls reviewed — call out by number any this change could trip (common suspects: #2 event-loop, #4 fire-and-forget writes, #18 missing migration, #20 `unit_name NOT NULL`, #23 RLS bypass, #27 downgrade cycle)
- [ ] Mobile/web never calls Anthropic or Stripe directly (pitfall #1, #10)

---

## After I approve

Implement in this order: migration → schema (pydantic) → service → router → tests → docs. When complete, run `/done` (once that command exists) or the equivalent gate: backend `pytest` + `ruff` + `bandit`, web `npm test` + `lint` + `typecheck` + `build`, `alembic check`, OpenAPI regen.

**If a section genuinely doesn't apply** (e.g., a pure-frontend tweak has no API contract), write `N/A — <reason>` for that section rather than skipping silently. "N/A" forces a conscious decision; omission hides it.
