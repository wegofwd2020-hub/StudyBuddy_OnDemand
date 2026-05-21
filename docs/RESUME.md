# RESUME — where to pick up

A git-tracked checkpoint so work can resume on any machine (Claude Code's local
memory does not travel; this file + GitHub issues do). Last updated: 2026-05-21,
`main` @ `f2b53fe`.

## ▶ Next task: finish **issue #363** — frontend unit tests + Playwright

Goal: get `main` CI fully green.

| CI job | State |
|---|---|
| Backend — Lint & Security | ✅ green |
| Frontend — Lint & Typecheck | ✅ green |
| Frontend — Unit Tests | ❌ red — **all-or-nothing**; 8/15 files fixed, ~7 remain |
| Playwright — Student Flow | ❌ red — can't run in-container (pitfall #26); needs host run |

**Remaining unit files (~7) and why they broke** (full detail + fix patterns in #363):
- `students-page` — RQ hook-mocks done; roster/invite/provision **content rewrite** pending (multi-section redesign).
- `subjects`, `curriculum-map` — **library-shelf accordion**: units/links render only after opening a `BookSpine`; need interaction-based rewrites + `getAllByText` for `sr-only` duplicates.
- `class-overview`, `curriculum-upload`, `at-risk`, `admin-content-review`, `admin-content-review-detail` — add React-Query hook mocks as needed + reconcile assertions with redesigned DOM.

**Reusable fix patterns established** (copy from these):
- React-Query mock incl. `useMutation` (invokes `mutationFn`+`onSuccess`), `useQueries`, `useQueryClient` → see `web/tests/unit/teachers-page.test.tsx` / `students-page.test.tsx`. Fixes the "No QueryClient set" crashes (RQ v5 throws).
- invite→provision rewrite → `teachers-page.test.tsx`.
- obsolete page → redirect-stub assertion → `demo-login-page.test.tsx`.
- copy/href drift → update shared `tests/e2e/data/*` `STRINGS` fixtures.

**Run frontend tests:** `cd web && npm test` (vitest). **Playwright (host only):** `cd web && npx playwright test`.

## Shipped this session (merged to `main`)
- **#359** — `curriculum_mgmt` capability (two-gate commission/review + umbrella; migration **0059** `teacher_capabilities`; top-bar Curriculum Management menu; capability assign UI). Design/spec: `docs/DESIGN_curriculum_mgmt_capability.md`, `docs/SPEC_curriculum_mgmt_capability.md`, `docs/CURRICULUM_ONBOARDING_FLOW.md`.
- **#360** — `/curriculum/upload` writes `owner_type='school'` (was defaulting to `platform`, tripping migration 0046 RLS under a non-superuser DB; pitfall #28).
- **#362** — backend lint job green + 8 frontend unit files modernized.

## Other open threads
- **#361** — non-superuser RLS test lane (`studybuddy_rls_tester`); audit done, build needs an env where the bootstrap role can `CREATE ROLE`/`DATABASE`.
- **Ashokan nav feedback** — AP-1 (too many nav items), AP-2 (rename "Class Overview"), AP-4 (Settings/Digest to top bar) still open in `docs/feedback/FEEDBACK_TRACKER.md`. AP-3 (Catalog vs Library) addressed by the Curriculum Management menu.

## Pick up on a different laptop
Prereqs: Docker/podman, Python 3.11+, Node 20, `gh` CLI.
1. `git clone …` (everything in-repo transfers).
2. **Securely copy** the gitignored secret files over (NOT via git): `./.env` and `web/.env.local`. Without them, `dev_start.sh` regenerates infra secrets but external keys (Auth0/Anthropic/Stripe/SMTP) are `REPLACE_ME` placeholders.
3. `./dev_start.sh` — builds images, runs migrations (incl. 0059), starts the stack. Use `./dev_start.sh test` for the backend suite (it provisions its own test Postgres — do **not** hand-craft `TEST_DB_URL` at a host postgres; see `gotcha_test_db_topology` lessons).
4. `cd web && npm ci && npx playwright install` for frontend unit + e2e tooling.
5. `gh auth login` for PR work.

Not in git (recreate or copy): `content_store/` (regenerate via pipeline, needs `ANTHROPIC_API_KEY`), `node_modules/`, local DB data (starts empty), Playwright browsers.
