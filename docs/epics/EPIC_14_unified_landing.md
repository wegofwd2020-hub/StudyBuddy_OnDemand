# Epic 14 — Unified Landing Page & Sign-in Modal

**Status:** 💭 Proposed 2026-04-24 — scope from the approved design spec,
awaiting go-ahead to file child issues and begin execution.

**Design source of truth:** [`studybuddy-docs/UNIFIED_LANDING_DESIGN.md`](https://github.com/wegofwd2020-hub/studybuddy-docs/blob/main/UNIFIED_LANDING_DESIGN.md) v0.1.0 + [`UNIFIED_LANDING_DESIGN_ADDENDUM.md`](https://github.com/wegofwd2020-hub/studybuddy-docs/blob/main/UNIFIED_LANDING_DESIGN_ADDENDUM.md) (v0.2.0-pending). Every requirement `UL-*-NNN` referenced below lives in those docs — this file is the work-breakdown.

---

## What it is

Consolidate the three existing landing surfaces — home, login-options, and
self-service demo — into **one role-aware landing page at `/`** with:

1. A unified hero leading with the value proposition.
2. A single sign-in entry point (modal) that is role-aware (Teacher or Admin
   on day one).
3. A prominent self-service demo CTA that requires no authentication.
4. A graceful off-ramp for students (App Store / Play Store badges — web
   never signs in a student).

Epic 13 (Branding Refresh) shipped the **copy** changes. Epic 14 ships the
**page architecture, auth surface, and routing** that the new copy lives in.

---

## Why now

- Three URLs fragment the marketing funnel and analytics (design §2.2).
- Returning teachers and admins hunt for "the right login page" — support
  load and bounce risk (BG-03).
- Students landing on web have no clear path to the mobile app (BG-04).
- Current sign-in stores JWTs in `localStorage` (addendum A-03) — a known
  security tech-debt item that the new landing is the natural moment to
  fix.
- Unified event schema unlocks funnel analysis (BG-05).

---

## Scope

### In scope (v1.0)

- New unified landing page at `/` (SSR, role cards, how-it-works, footer with
  store badges).
- New sign-in modal (Teacher + School admin roles, email + password).
- `first_login=true` forced-reset redirect (addendum A-04).
- Session cookie migration: `localStorage` → `httpOnly` + `Secure` +
  `SameSite=Lax` (addendum A-03).
- Legacy redirects (`/login`, `/signin`, `/login/teacher`, `/login/admin`,
  `/get-started`, `/try`).
- Telemetry events UL-T-001..011.
- Performance budgets (Lighthouse ≥ 90 mobile) + bundle size ≤ 150 KB gzipped.
- WCAG 2.1 AA compliance + axe-core automated checks + manual SR/keyboard
  passes.
- Rate-limit reconciliation with existing auth rate limiter (5/15m IP +
  10/hr account).
- E2E coverage for personas P1/P2/P3/P5 + all legacy redirects.

### v1.1 fast-follow (separate epic or fast-follow tickets)

- Google OAuth 2.0 SSO for Teacher + Admin (design §8).
- School-domain verification on first SSO sign-in.

### Out of scope

- Parent web sign-in (v1.2+).
- Direct student web sign-in (Kivy + App/Play Store only).
- Microsoft 365 / Entra SSO (v2.0+, demand-driven).
- Passwordless / magic-link / WebAuthn.
- Multi-language landing page (i18n) — Epic 13 handles FR/ES copy on existing
  surfaces only; unified-landing i18n is deferred.
- Formal A/B test infrastructure.
- Redesign of `/teacher` or `/admin` dashboards — only the entry point
  changes.

---

## Tickets

Severity legend: **HIGH** — user-visible blocker; **MEDIUM** — correctness or
quality; **LOW** — polish or nice-to-have.

### UL-1 — Route scaffold & legacy redirects

**File:** `web/next.config.ts`, `web/middleware.ts` (new), `web/app/(public)/page.tsx`

**Scope:** Add Next.js `redirects()` for all entries in design §5.2; add
`middleware.ts` to preserve UTM query params through 301 redirects. Ship an
empty SSR `/` route (placeholder) that the rest of the epic fills in.

**Acceptance:**
- `curl -I http://localhost:3000/login` → `301` with `Location:
  /?signin=true` (and UTM params preserved).
- Every row in design §5.2 covered; one Playwright spec asserts each.
- `web/tests/fixtures/legacy_urls.csv` committed and consumed by the spec.

**Requirements covered:** UL-F-020, UL-F-021.

**Severity:** HIGH — foundational; everything else imports routing.

---

### UL-2 — Landing page SSR scaffold + hero

**File:** `web/app/(public)/page.tsx`, `web/components/landing/Hero.tsx` (new).

**Scope:** Server-rendered `/` with sticky header (logo + nav placeholder +
Demo / Sign-in buttons) and hero (H1, subcopy, two primary CTAs). Responsive
at mobile / tablet / desktop breakpoints.

**Acceptance:**
- `curl http://localhost:3000/` returns HTML with the H1 copy present
  pre-hydration (verify via `view-source`).
- Visual parity with design §6 wireframe at desktop and mobile breakpoints
  (Playwright screenshot test).
- `next build` output confirms the `/` route is marked `○ (Static)` or
  `λ (Dynamic)` — **not** `◐ (SSR+client)` for initial render.

**Requirements covered:** UL-F-001, UL-F-002, UL-NF-006, UL-NF-010.

**Severity:** HIGH.

---

### UL-3 — Landing page content sections

**File:** `web/components/landing/{WhoItsFor,HowItWorks,DemoPreview,SocialProof,Footer}.tsx` (all new).

**Scope:** "Who it's for" three-card row (Students/Teachers/Admins), "How it
works" three-step strip, live demo preview placeholder, social-proof
placeholder, footer with App Store + Play Store badges and legal links. The
Students card links to the stores only — no web sign-in button.

**Acceptance:**
- Playwright spec asserts the three role cards render with the correct CTAs
  per design §6.
- Students card contains `<a>` tags pointing at App Store and Play Store
  URLs and **no** sign-in button.
- Footer contains visible `<a>` to Privacy, Terms, Contact.

**Requirements covered:** UL-F-004, UL-F-005, UL-F-006, UL-F-007, UL-F-008,
UL-F-009.

**Severity:** MEDIUM.

---

### UL-4 — Sign-in modal: shell, role selector, a11y

**File:** `web/components/landing/SignInModal.tsx` (new), `web/hooks/useSignInModal.ts` (new).

**Scope:** Lazy-loaded modal component (Next.js `dynamic()`), radio-group
role selector with `<fieldset>`/`<legend>`, focus trap, `Esc` + backdrop-
click close, return focus to invoker. Opens on `?signin=true` and on the
three CTAs (header, Teachers card, Admins card).

**Acceptance:**
- Keyboard-only walkthrough: `Tab` reaches role radios → email → password →
  Sign in → Forgot password → Close, with visible focus.
- axe-core scan in modal-open state reports 0 serious/critical violations.
- Role pre-selection honors `?role=` query param; falls back to
  `sb_last_role` cookie; defaults to Teacher.
- Screenshot test at mobile breakpoint asserts full-screen-sheet layout.

**Requirements covered:** UL-F-010..013, UL-F-022..023, UL-A-001..008,
UL-NF-005.

**Severity:** HIGH — the sign-in surface is the critical path for returning
users.

---

### UL-5 — Sign-in modal: auth wiring (local + admin tracks) + error states

**File:** `web/lib/api/local-auth.ts`, `web/components/landing/SignInModal.tsx` (update).

**Scope:** POST email/password to the role-appropriate endpoint per
addendum A-02 (Teacher/school_admin → `POST /auth/login`; admin → `POST
/admin/auth/login`). Render inline error states per design §7.5. Prevent
double-submission. Server-side 302 to `/teacher` or `/admin` on success.

**Acceptance:**
- Integration test (Playwright) covers: valid teacher → lands on
  `/teacher`; valid admin → lands on `/admin`; invalid password →
  inline "Email or password is incorrect"; locked account → "Too many
  attempts. Try again in 15 minutes…"
- Role-mismatch copy renders exactly per §7.5.
- Double-click on Sign in fires one network request, not two (verified via
  Playwright `page.on('request')`).

**Requirements covered:** UL-F-014..019, UL-S-004, UL-S-009.

**Severity:** HIGH.

---

### UL-6 — `first_login=true` forced-reset redirect

**File:** `web/components/landing/SignInModal.tsx` (update), `web/app/(school)/school/change-password/page.tsx` (already exists — verify integration).

**Scope:** After successful sign-in, if the JWT payload contains
`first_login: true`, redirect to `/school/change-password?required=1`
before the dashboard renders (addendum A-04). Runs for both Teacher and
Admin tracks.

**Acceptance:**
- Provision a new teacher via `POST /schools/{id}/teachers` (gets
  `first_login=true`); sign in via the new modal; URL ends on
  `/school/change-password?required=1` without visiting `/teacher` first.
- After changing password, subsequent sign-ins go directly to `/teacher`
  with no redirect.

**Requirements covered:** UL-F-024, UL-F-025, UL-F-026 (addendum A-04).

**Severity:** HIGH — compliance with the provisioned-accounts flow.

---

### UL-7 — Session cookie migration: `localStorage` → `httpOnly`

**File:** `backend/src/auth/router.py`, `backend/src/auth/admin_router.py`,
`web/lib/api/*.ts`, `web/middleware.ts`.

**Scope:** Replace `localStorage['sb_token']`, `localStorage['sb_teacher_token']`,
`localStorage['sb_admin_token']` with `httpOnly` + `Secure` + `SameSite=Lax`
cookies, issued server-side. Update axios clients to rely on the
browser's cookie jar. Add backend middleware to read the cookie if the
`Authorization` header is absent. Document the migration path so existing
local-auth sessions don't black-hole.

**Acceptance:**
- Login response sets `Set-Cookie: sb_session=...; HttpOnly; Secure;
  SameSite=Lax` (verified in Playwright).
- `document.cookie` in DevTools shows the cookie is **not** reachable from
  JS.
- `localStorage.getItem('sb_teacher_token')` returns `null` after
  successful sign-in on the new flow.
- All protected routes still work: one Playwright walk-through per role.

**Requirements covered:** UL-S-007, UL-S-008, UL-S-011 (addendum A-03).

**Severity:** HIGH — security hardening; backs UL-S-007 (MUST).

---

### UL-8 — Rate limiting + CSRF alignment

**File:** `backend/src/core/rate_limit.py`, `backend/src/auth/router.py`,
`web/middleware.ts`.

**Scope:** Reconcile spec UL-S-003 (5 attempts / IP / 15 min + 10 / account /
hour) with the existing 10/min IP limiter (addendum A-06). Add a per-
account (per-email) limiter keyed in Redis. Wire CSRF protection via
double-submit token or SameSite=Lax cookie + Origin/Referer check.

**Acceptance:**
- 6 failed sign-ins from the same IP within 15 min returns 429 with
  `Retry-After`.
- 11 failed sign-ins for the same account across rotating IPs returns 423
  `account_locked`.
- CSRF: a cross-origin `fetch` to `/auth/login` with a forged cookie is
  rejected with 403 (Playwright test runs from `evil.localhost:3001`).

**Requirements covered:** UL-S-002, UL-S-003, UL-S-010, UL-S-012 (addendum
A-06).

**Severity:** HIGH.

---

### UL-9 — Telemetry events

**File:** `web/lib/analytics.ts` (new), component call sites.

**Scope:** Emit the seven events in design §13 plus the two constraints
(UL-T-010, UL-T-011). No raw PII in payloads; `session_id` persists pre/post
sign-in. Events fire into the existing analytics pipeline via the web
analytics client (see ADR-xx — TBD on exact sink).

**Acceptance:**
- Each event has at least one Playwright assertion via `page.on('request')`
  that the payload shape matches the spec.
- Grep of the production bundle (`next build && grep`) finds no literal
  email strings in the analytics payload schemas.

**Requirements covered:** UL-T-001..011.

**Severity:** MEDIUM — not a ship blocker, but required for the funnel
analysis that motivates the epic.

---

### UL-10 — Performance budgets + Lighthouse CI

**File:** `web/lighthouserc.json` (new), `.github/workflows/lighthouse.yml`
(new).

**Scope:** Wire Lighthouse CI to run against `/` on every PR. Enforce
UL-NF-001..004 thresholds. Fail CI if bundle size exceeds 150 KB gzipped.

**Acceptance:**
- A failing run (e.g., unoptimised hero image ≥ 400 KB) blocks merge with
  the actionable lighthouse report link.
- A passing run on `main` stays above 90 on all four categories.

**Requirements covered:** UL-NF-001..007, UL-NF-010, AC-03, AC-07.

**Severity:** MEDIUM.

---

### UL-11 — Accessibility pass

**File:** `web/tests/a11y/unified-landing.spec.ts` (new).

**Scope:** axe-core automated checks on `/` and on modal-open state; one
manual NVDA-on-Windows or VoiceOver-on-macOS pass of the sign-in flow; one
keyboard-only pass covering P2 and P3 personas end-to-end. Capture findings
in `web/tests/a11y/UNIFIED_LANDING_FINDINGS.md`.

**Acceptance:**
- axe reports 0 serious/critical on both states.
- Manual test log signed off by a second pair of eyes (committed as a PR
  review approval from a reviewer other than the author).

**Requirements covered:** UL-A-001..009, AC-04, AC-05.

**Severity:** HIGH — WCAG 2.1 AA is a MUST in UL-A-001.

---

### UL-12 — E2E coverage

**File:** `web/tests/e2e/unified-landing.spec.ts` (new).

**Scope:** Playwright flows per AC-01: P1 demo (landing → /demo), P2 teacher
sign-in (modal → /teacher), P3 admin sign-in (modal → /admin), P5 student
redirect (store badge click opens correct external URL), every legacy
redirect from §5.2.

**Acceptance:**
- One spec file, one test per persona + one per legacy redirect row.
- `web/tests/e2e/README.md` updated with run instructions if the host-vs-
  container quirk from CLAUDE.md pitfall #26 applies.

**Requirements covered:** AC-01, AC-02.

**Severity:** MEDIUM.

---

### UL-13 — Requirement → test traceability matrix

**File:** `web/tests/TRACEABILITY.md` (new).

**Scope:** Table mapping every `UL-*-NNN` ID to the test(s) that cover it.
CI check (simple script, no framework) fails if a requirement ID appears in
`UNIFIED_LANDING_DESIGN.md` without a row in the matrix.

**Acceptance:**
- Matrix committed with every ID from v0.2.0 of the design doc.
- A deliberate mis-merge (new requirement added without matrix row) fails
  CI with a clear error message.

**Requirements covered:** design §15.2.

**Severity:** LOW (tooling), but pays off for Epic 14 and every subsequent
design doc.

---

## Open questions (from design §16)

These MUST be resolved before the corresponding ticket can close. Keeping
them visible here as a call-out — the design doc is canonical.

| # | Blocks | Question | Owner |
|---|---|---|---|
| Q-01 | UL-8 | CAPTCHA on sign-in? Or rate-limit only in v1.0? | Security |
| Q-02 | UL-5 | "Remember me" checkbox, or long-lived session default? | Product |
| Q-03 | UL-1 | Final list of legacy URLs (needs `web/` directory audit) | Frontend |
| Q-04 | UL-2 | Brand design tokens: existing system or define as part of this work? | Design |
| Q-05 | UL-5 | Does `/forgot-password` exist already, or build for v1.0? | Backend |
| Q-06 | UL-3 | Does the demo sandbox set a cookie so returning visitors skip the welcome? | Product |
| Q-07 | UL-2 | Marketing header (Product / Pricing / For Schools) in v1.0 or defer? | Product |
| Q-08 (addendum) | UL-3 | Do the App/Play Store badge links point at placeholder URLs for v1.0? | Product |

---

## Dependencies

- **Epic 13 (Branding Refresh)** — ✅ shipped. Copy lands in the surfaces
  Epic 14 rebuilds around.
- **Epic 9 (Accessibility & Personalization)** — open issue #189 (3 axe
  rules disabled in persona e2e suite). UL-11 should close or subsume
  whatever of #189 still applies to the unified landing.
- **Auth rate-limit PR #266** (merged) — UL-8 builds on the CF-aware IP
  resolution and fail-open semantics added there.

---

## Success metrics (post-launch, 2-week window)

- Marketing funnel: single-URL conversion rate ≥ sum of current three
  landing surfaces (BG-01..02).
- Support: sign-in-related tickets reduce by ≥ 50% (BG-03).
- Performance: Lighthouse mobile stays ≥ 90 across all four categories on
  every production build.
- Accessibility: axe-core finds 0 serious/critical on every PR.

---

## Changelog

| Version | Date | Author | Change |
|---------|------|--------|--------|
| 0.1.0 | 2026-04-24 | Siva Palaniappan (drafted with Claude) | Initial draft — 13 tickets covering v1.0 scope. |
