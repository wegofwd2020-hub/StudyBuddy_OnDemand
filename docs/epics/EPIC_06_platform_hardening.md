# Epic 6 — Platform Hardening

**Status:** 💭 Your call

---

## What it is

Close the known gaps in test coverage, performance, and security before a
production launch with real student data. Not a feature epic — a quality and
confidence epic. Can run in parallel with other epics.

---

## Current state

### Test coverage
- **Backend:** 678+ tests across all phases. Core flows well-covered. Known gaps:
  - No end-to-end tests covering the full student study flow (login → lesson → quiz → progress)
  - Admin content review workflow tests exist but are thin on edge cases
  - Stripe webhook handler has happy-path tests only; no tests for retried events, partial failures, or out-of-order delivery
  - `GET /admin/help/interactions` (just added) has no tests yet
- **Web frontend:** TypeScript type-check only (`npm run typecheck`). No component tests, no Playwright/Cypress E2E tests.
- **Mobile:** Logic unit tests only (SyncManager, LocalCache). No integration tests.
- **Pipeline:** Mocked Anthropic + TTS. No tests for the `--force` flag idempotency logic with real file state.

### Performance
- Hot read path (JWT verify → L1 → L2 → DB) is designed but not load-tested
- No baseline benchmark exists for: concurrent students, concurrent pipeline jobs, or burst analytics writes
- Connection pool sizes (asyncpg `min=5, max=20`) are un-tuned for production traffic

### Security
- Bandit scans referenced in conventions but no CI step enforces them
- COPPA consent flow exists in the data model (`account_status = 'active'` gate) but is not covered by tests
- `POST /help/ask` and `POST /help/feedback` are public endpoints — tested for rate limiting in isolation but not load-tested for abuse resilience
- No automated dependency CVE scanning (e.g. `pip audit`, `npm audit` in CI)
- JWT expiry and refresh token revocation are implemented but not tested for edge cases (expired token, revoked token mid-session)

### Observability gaps
- Prometheus metrics exist but no alerting rules are written
- No SLO definitions (what latency is "acceptable"? what error rate triggers an alert?)
- Help widget usage (questions asked, feedback ratio) not yet surfaced in any dashboard

---

## Why it matters

Shipping with real student data under FERPA/COPPA without this work is a legal
and reputational risk. Performance gaps discovered in production are harder to
fix than in staging. A security incident before launch ends the company.

---

## Rough scope

| Phase | What gets built |
|---|---|
| K-1 | CI hardening: Bandit + `pip audit` + `npm audit` on every PR; block merge on high-severity findings |
| K-2 | E2E test suite: Playwright covering student login → lesson → quiz → progress flow |
| K-3 | Stripe webhook hardening: tests for retry, idempotency, and out-of-order event delivery |
| K-4 | Load testing: k6 scripts for the hot read path and concurrent pipeline jobs; establish baselines |
| K-5 | SLO definitions + Grafana alerting: p95 latency < 200ms, error rate < 0.1%, pipeline job failure rate < 5% |
| K-6 | COPPA/FERPA test coverage: consent gate, parental consent flow, cross-school data isolation assertions |

---

## Prioritisation note

K-1 (CI hardening) and K-3 (Stripe webhook) are the highest-value, lowest-effort
items and could be done in a single session each. K-4 (load testing) requires a
staging environment (Epic 2) to be meaningful. K-6 (COPPA/FERPA) is legally
important but lower urgency until a real school is onboarded.

---

## Open questions

1. **When?** Is this a pre-condition for launch (must complete before any school uses production), or an ongoing background effort?
2. **E2E target:** Playwright tests against a local Docker stack, or against a deployed staging environment?
3. **Load testing targets:** What scale defines success? 100 concurrent students? 1,000? This depends on the first school's size.
4. **CVE scanning:** Automated block on `pip audit` findings? Some dependencies have known low-severity CVEs with no fix available — need a policy for those.
5. **SLO ownership:** Who is on-call when an alert fires? Does an on-call rotation exist, or is this solo?

---

## Your decisions / notes

> Add your thoughts here. Even rough bullet points are enough to start.

-
-
-
