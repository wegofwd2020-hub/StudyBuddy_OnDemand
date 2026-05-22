# RESUME — where to pick up

A git-tracked checkpoint so work can resume on any machine (Claude Code's local
memory does not travel; this file + GitHub issues do). Last updated: 2026-05-22,
`main` @ `b49bdbd`.

## ▶ Issue #363 — DONE (unit tests ✅ + Playwright ✅)

Goal: get `main` CI fully green.

| CI job | State |
|---|---|
| Backend — Lint & Security | ✅ green |
| Frontend — Lint & Typecheck | ✅ green |
| Frontend — Unit Tests | ✅ green — all 63 files / 821 tests pass; typecheck clean |
| Playwright — Student Flow | ✅ green — 134 passed, 7 fixme-skipped, 0 failing (host, `--workers=1`) |

**Playwright — DONE.** 16 drift specs fixed for the Epic 16 public-site redesign (2026-05-22):
- `landing-page` — banner alt, hero "Lessons, always current.", 6 new feature cards, footer CTA → /school/register, nav "Sign in" → /signin; PUB-06 testimonials section was removed → repurposed to the Tour Gateway section.
- `pricing-page` — Platform Starter ($0) / School Pro (~$5) / School Enterprise (Custom); plan names are `div`s not headings (use `getByText`); CTAs + 7 FAQ items rewritten.
- `public` — hero CTA regex → /register your school/i; pricing prices → $0 / ~$5 / Custom.
- `student-login-page` — local-auth link is now "Sign in here" → /signin.
- `student_flow` — hero heading via the shared landing fixture; `getByText("Cell Biology").first()` (BookSpine renders title twice); nav "Sign in" needs `exact: true` (hero "Already a teacher? Sign in" also matches).

**Host run notes:** `gh` + Playwright Chromium are now installed. Run from `web/` on the host
(not the Alpine container — pitfall #26). The ~18 timeouts seen with the default parallel run are
Turbopack dev-server cold-compile contention, not real failures — they pass with `--workers=1`.
CI uses `reuseExistingServer:false` + a built server, so it doesn't hit this.

**Frontend unit tests — DONE.** All 9 remaining files fixed (2026-05-22):
- `reports-overview` — sub-nav is admin-only after #358; render `SchoolNav` as `school_admin`.
- `subjects`, `curriculum-map` — **library-shelf accordion**: open the `BookSpine` before asserting on units/links; spine title appears twice (visible + `sr-only`) so match by `button` name or `getAllByText`. curriculum-map's old "Lab badge" is now an Experiment link in the `Toc`.
- `class-overview`, `students` — page split into useQuery(classrooms)+`useQueries`; branch the query mock by `queryKey` and return `[]` for classrooms; students roster/invite/bulk-enrol moved to the **school_admin** view (render as admin); count badge → "Enrolled students" card.
- `at-risk` — **concept rewrite**: per-unit "curriculum health" → per-student "At-Risk Students" (Needs attention / Reviewed + Remind/Mark-seen). Fixture + test rewritten to `AtRiskListResponse`.
- `curriculum-upload` — XLSX flow now behind an "XLSX Upload" tab (default is JSON); click the tab first.
- `admin-content-review`, `admin-content-review-detail` — add `useMutation`/`useQueryClient`/`useAdmin` mocks; the mutation stub must invoke `mutationFn`+`onSuccess`; branch the detail-page query mock so the admin-users + warnings queries return inert values.

**Next: Playwright — Student Flow** (host-only run, pitfall #26).

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
