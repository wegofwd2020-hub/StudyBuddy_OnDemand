# Design — Self-Service Demo Access Request

**Status:** Draft v0.2 (design only — not yet implemented)
**Date:** 2026-05-09
**Author:** Sivakumar (with Claude design assist)
**Companion docs:**
- [`DEMO_LAUNCH_PLAN.md`](./DEMO_LAUNCH_PLAN.md) — the May 17 launch runbook (this feature is post-launch unless explicitly pulled forward)
- [`DESIGN_HELP_SYSTEM.md`](./DESIGN_HELP_SYSTEM.md) — naming-convention reference

> **Long-term framing.** `demo.studybuddy.app` is intended as a permanent demo
> environment, not a launch-day artefact. Where there's a tension between
> "easy to ship for May 17" and "ages well over 12+ months", this design
> picks the latter. The most consequential expression of that is §3.5 —
> demo logins reuse the **canonical** login routes (`/school/login`,
> `/login`) rather than dedicated `/demo/*` paths.

---

## 1 · What it is

A self-service path on `https://demo.studybuddy.app` that lets a visitor:

1. Submit their **name + email** to request demo access
2. Confirm their **email** via a one-click link
3. Receive **two login URLs** — one for the Grade 11 teacher view, one for the Grade 11 student view
4. Use either URL **any number of times within 7 days**

After 7 days the URLs stop working automatically. The visitor never sees a password.

The two login URLs always resolve to the **same shared accounts** (one shared `demo-teacher`, one shared `demo-student`) — see §6 for why.

## 2 · Decided constraints

| # | Decision | Date |
|---|---|---|
| 1 | **Daily cap: 20 demo requests** across all visitors | 2026-05-09 |
| 2 | **Email verification required** — confirm-link before credentials issued | 2026-05-09 |
| 3 | **Multi-use tokens** — same URL works any number of times within 7 days | 2026-05-09 |
| 4 | **From: `demo@studybuddy.app`** via Zoho SMTP | 2026-05-09 |

## 3 · End-to-end flow

```
Visitor                Demo site                 Backend                  Email (Zoho)
   │                      │                         │                        │
   │ 1. submits {name,    │                         │                        │
   │    email} on /demo   │                         │                        │
   │ ───────────────────▶ │                         │                        │
   │                      │ POST /demo/request      │                        │
   │                      │ ──────────────────────▶ │                        │
   │                      │                         │ checks daily cap (20)  │
   │                      │                         │ inserts demo_request   │
   │                      │                         │ status=pending_email   │
   │                      │                         │ generates verify_token │
   │                      │                         │ ───────────────────▶   │
   │                      │                         │              "Confirm your │
   │                      │                         │              email" template │
   │                      │  "Check your inbox"     │                        │
   │                      │ ◀────────────────────── │                        │
   │  thank-you screen    │                         │                        │
   │ ◀─────────────────── │                         │                        │
   │                      │                         │                        │
   │ 2. clicks confirm    │                         │                        │
   │    link in email     │                         │                        │
   │ ─────── GET /demo/confirm?token=… ───────────▶ │                        │
   │                      │                         │ validates verify_token │
   │                      │                         │ flips → confirmed      │
   │                      │                         │ generates teacher_token│
   │                      │                         │ generates student_token│
   │                      │                         │ both 7d TTL, multi-use │
   │                      │                         │ ───────────────────▶   │
   │                      │                         │              "Your demo creds" │
   │                      │                         │              with 2 login URLs│
   │  "Email sent —       │                         │                        │
   │   credentials on     │                         │                        │
   │   their way"         │                         │                        │
   │ ◀─────────────────── │                         │                        │
   │                      │                         │                        │
   │ 3a. clicks teacher login URL (any time within 7d)                       │
   │ ── GET /school/login?demo_token=… ──▶ canonical route's auth middleware │
   │                                         sees demo_token, validates,     │
   │                                         sets session as demo-teacher@   │
   │                                         shared account → 302 to /school │
   │                                                                         │
   │ 3b. clicks student login URL (any time within 7d)                       │
   │ ── GET /login?demo_token=… ─────────▶ same middleware on the canonical  │
   │                                         student-login route → session   │
   │                                         as demo-student@ → 302 to       │
   │                                         /student                        │
```

**Note on the URLs.** Both login URLs are the **canonical login pages** of
the application — the same routes a real teacher or student would hit.
The demo-token mechanism is implemented as auth middleware that lives on
those routes (see §3.5), invisible to non-demo traffic. There are no
`/demo/teacher/login` or `/demo/student/login` paths.

## 3.5 · Why reuse the canonical login routes (not dedicated `/demo/*` paths)

### The decision

The demo-credential URLs in the email are **the same login URLs as
production** — `https://demo.studybuddy.app/school/login` for the teacher
view and `https://demo.studybuddy.app/login` for the student view. Each
carries a `?demo_token=<random>` query param.

Auth middleware on those routes recognises `demo_token`, validates it
against the `demo_request` table (§4), sets a regular session cookie tied
to the appropriate shared account (§6), and redirects to the dashboard.
For non-demo traffic (no `demo_token`), the routes behave **exactly** as
they do today — the demo path is an additive branch in the auth layer.

### Why this matters more than it looks

| Problem with dedicated `/demo/{teacher,student}/login` | How canonical-route reuse avoids it |
|---|---|
| URL surface drift over time (real teacher vs demo teacher login pages diverge in copy, branding, error handling) | One login surface — every change to the real login page applies to demo evaluators automatically |
| Demo evaluators see a login page that looks slightly different from "the real product" | Evaluators see the real product login, which is itself part of the demo |
| Demo URL paths leak into the codebase (Next.js routes, FastAPI routers, e2e tests) and add maintenance tax | Zero new public URL paths; demo logic lives entirely in middleware |
| If `demo.studybuddy.app` becomes a long-term environment, the `/demo/*` paths must be supported indefinitely or break old emailed links | Canonical routes are stable as long as the product exists; emailed links age well |
| Operator confusion: "is `/school/login` a real login or a demo login?" | One answer for both |

### Implementation shape (per route)

Pseudo-code for the canonical login middleware (FastAPI / Next.js, same
shape):

```python
async def login_route_middleware(request: Request, role: Role):
    demo_token = request.query_params.get("demo_token")

    if demo_token:
        demo_id = validate_demo_token(demo_token, role)   # raises 403/404
        session = create_session(
            user=SHARED_DEMO_USERS[role],   # demo-teacher@ or demo-student@
            origin="self_service_demo",
            demo_request_id=demo_id,
        )
        response = RedirectResponse(DASHBOARD[role])
        set_session_cookie(response, session)
        return response

    # Otherwise: render the canonical login form (existing behaviour)
    return render_login_page(request, role)
```

`SHARED_DEMO_USERS` is the seed-script mapping (§6 Option B). `origin`
on the session lets us tag analytics events with whether the user came
in via self-service demo, named persona walkthrough, or real auth — useful
for understanding evaluator vs. customer behaviour later.

### Wrong-link handling

A visitor who copies the wrong URL (clicks the student URL but pastes
the teacher token by mistake) hits the canonical login page with a token
that doesn't exist in *that role's* column. The middleware can either:

1. **Render the regular login form** (treat unknown token as "not a demo
   login") — simplest; visitor is mildly confused but isn't blocked
2. **Cross-check the other role's column** and 302-redirect to the
   correct login route — requires one extra query, gives nicer UX

I'd ship (1) first; add (2) if real evaluators trip on this.

### What's not affected

- The `POST /demo/request` and `GET /demo/confirm` endpoints (§5) keep
  the `/demo/*` prefix because they're one-time *request-handling* flows,
  not authentication surfaces. They never replace a canonical product
  page, so there's no benefit to dressing them up as canonical routes.
- The demo-request **form** at `/demo` (§11) keeps its dedicated path — a
  visitor needs an entry point to *request* demo access, and that entry
  point is itself the demo-specific affordance.

## 4 · Data model — one new table

```sql
CREATE TABLE demo_request (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name            TEXT NOT NULL,
  email           CITEXT NOT NULL,
  status          TEXT NOT NULL CHECK (status IN
                    ('pending_email','confirmed','expired','revoked')),

  -- email-confirm step (single-use, 24h)
  verify_token        TEXT UNIQUE,
  verify_expires_at   TIMESTAMPTZ,
  verified_at         TIMESTAMPTZ,

  -- credentials step (multi-use within 7d)
  teacher_token            TEXT UNIQUE,
  student_token            TEXT UNIQUE,
  credentials_expires_at   TIMESTAMPTZ,

  -- audit
  request_ip      INET NOT NULL,
  request_ua      TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_used_at    TIMESTAMPTZ,           -- last successful demo login
  use_count       INT NOT NULL DEFAULT 0
);

CREATE INDEX ON demo_request (email);
CREATE INDEX ON demo_request (created_at DESC);
CREATE INDEX ON demo_request (verify_token)  WHERE status = 'pending_email';
CREATE INDEX ON demo_request (teacher_token) WHERE status = 'confirmed';
CREATE INDEX ON demo_request (student_token) WHERE status = 'confirmed';
```

**Token format.** Random 256-bit URL-safe strings (`secrets.token_urlsafe(32)`),
not JWTs — DB-backed so revocation is a single `UPDATE`. Multi-use is just
"no atomic invalidation on read"; we increment `use_count` and update
`last_used_at` for telemetry.

**Status transitions.**

```
pending_email ──(confirm link clicked, < 24h)──▶ confirmed
pending_email ──(verify_expires_at passed)─────▶ expired
confirmed     ──(credentials_expires_at passed)▶ expired
{any}         ──(operator action)──────────────▶ revoked
```

## 5 · API surface — 2 new routes + middleware on 2 existing routes

### New routes (demo-specific, one-time flows)

| Method | Path | Purpose |
|---|---|---|
| `POST /api/v1/demo/request` | submit name + email | Validates daily cap; insert row; send "confirm your email"; respond `202 Accepted` (no info leak about whether the email already exists) |
| `GET /api/v1/demo/confirm?token=…` | confirm email | Validates `verify_token`; flips status → `confirmed`; sends credentials email; redirects to "credentials sent" page |

### Auth middleware on canonical login routes

| Route | Existing behaviour | Demo-mode addition |
|---|---|---|
| `GET /school/login` | Renders teacher-login form | If `?demo_token=…` present, validate against `demo_request.teacher_token`; on success, set session as shared `demo-teacher` account and 302 to `/school` |
| `GET /login` (student) | Renders student-login form | If `?demo_token=…` present, validate against `demo_request.student_token`; on success, set session as shared `demo-student` account and 302 to `/student` |

The canonical login forms are unchanged for non-demo traffic. The demo
branch is implemented as an **additive middleware** (see §3.5) — when
`demo_token` is absent, the existing login flow runs unmodified.

### Token validation pseudo-code

```python
def validate_demo_token(token: str, kind: Literal['teacher','student']):
    row = db.execute(
        "SELECT id, status, credentials_expires_at "
        f"FROM demo_request WHERE {kind}_token = :t",
        {"t": token}
    ).first()
    if not row:                          raise HTTPException(404)
    if row.status != 'confirmed':        raise HTTPException(403, 'revoked')
    if row.credentials_expires_at < now: raise HTTPException(403, 'expired')

    db.execute(
        "UPDATE demo_request SET use_count = use_count + 1, "
        "last_used_at = NOW() WHERE id = :id", {"id": row.id}
    )
    return row.id
```

Multi-use means **no decrement on read**; the only gate is the expiry
timestamp. Revocation = `UPDATE demo_request SET status = 'revoked' WHERE …`
(operator action, e.g. abuse-detection cron).

## 6 · Shared accounts — concrete picks (decided 2026-05-09)

Both demo URLs resolve to **dedicated shared demo accounts** sitting
inside MilfordWaterford's existing `Grade 11 — Science` classroom. We
chose this over reusing the named personas (Linda Ronstad, Fatima
Al-Hassan, Liam O'Brien) so that **self-service evaluator state never
collides with sales-walkthrough state**.

### The classroom

| Field | Value |
|---|---|
| Classroom name | `Grade 11 — Science` |
| Curriculum | `default-2026-g11-science` ("Grade 11 Science 2026") |
| Lead teacher (named) | Linda Ronstad — `linda.ronstad@milfordwaterford.edu` |
| Students (named) | Fatima Al-Hassan, Liam O'Brien |

### The new accounts to add

Both go in `backend/scripts/seed_demo_milfordwaterford.py`:

| Field | Demo teacher | Demo student |
|---|---|---|
| Display name | `Demo Teacher (G11 Science)` | `Demo Student (G11 Science)` |
| Email | `demo-teacher@studybuddy.app` | `demo-student@studybuddy.app` |
| Password (server-only — never emailed) | `<openssl rand -hex 16>` (rotated nightly by §9 reset) | same |
| Role | `teacher` | (student) |
| School | MilfordWaterford Local School | same |
| Classroom enrolment | Co-teacher on `Grade 11 — Science` | Student in `Grade 11 — Science` |
| Grade | 11 | 11 |
| Stream | Science | Science |
| Account expiry | 2099-12-31 (effectively non-expiring) | same |

### What an evaluator sees

**As `demo-teacher@`:**
- Their classroom roster shows **3 students**: Fatima, Liam, and
  `demo-student@` (themselves' counterpart). Real-looking class with
  populated names — not a single ghost student.
- Co-teacher with Linda Ronstad — class overview, weekly digest,
  at-risk list all draw from Linda's curated class data plus any state
  the demo accounts have generated since the last nightly reset.
- **Library is pre-populated**: `Grade 11 Science 2026` (curriculum
  `default-2026-g11-science`) is already adopted into MilfordWaterford's
  library via `seed_demo_milfordwaterford.py`. The teacher sees a
  populated library on first login — no "import a curriculum" step
  required for the demo flow. Write actions that would extend or
  re-build the library are blocked; see §6.5.

**As `demo-student@`:**
- Enrolled in `Grade 11 — Science`. Sees the same lessons, quizzes, and
  tutorials as Fatima and Liam.
- Classmates panel shows Fatima and Liam (real-looking, not a solo
  enrolment).
- Progress, quiz attempts, etc. are scoped to `demo-student@` and get
  reset nightly (§9).

### Why "shared" is OK for this demo

A nightly cron (§9) **resets the shared `demo-teacher@` and
`demo-student@` accounts to the seed-script baseline** — passwords
rotated, quiz attempts cleared, edits reverted, entitlements reset.
State is intentionally ephemeral. Concurrent users may briefly see each
other's quiz attempts or dashboard updates during the same UTC day, but
the disclosure (§7) makes that explicit and the nightly reset wipes it
cleanly. Real isolation is not worth the provisioning complexity for
this audience size.

### What we're explicitly NOT doing

- **Not reusing Linda Ronstad / Fatima Al-Hassan / Liam O'Brien as the
  shared accounts.** They stay reserved for named-persona sales
  walkthroughs. The two paths use the same classroom and curriculum
  data, so a sales call and a self-service evaluator see the same
  product surface — only the *user* logging in differs.
- **Not creating one demo classroom per evaluator.** Pool/per-request
  isolation was rejected in the original design conversation; nightly
  reset of two shared accounts is the chosen middle ground.

## 6.5 · Demo-account write scope (decided 2026-05-10)

The demo teacher is **read-mostly with a curated set of write actions**.
Anything that costs real LLM spend, modifies cross-school platform
state, or extends the library is blocked. Anything that's part of the
core teacher evaluation surface (content review, classroom interaction,
feedback) is allowed and gets reset nightly.

### Allowed vs. blocked

| Action | Allowed? | Why |
|---|---|---|
| Browse library / view adopted curricula | ✅ | Core demo surface |
| View classroom roster, weekly digest, at-risk list | ✅ | Core demo surface |
| View / play lessons, quizzes, tutorials (as student) | ✅ | Core demo surface |
| **Content review flow (Epic 12)** — view drafts, leave annotations, approve / reject / publish overrides | ✅ | Meaty teacher-flow surface; in-flight reviews are intentionally trashed by the nightly reset and that's OK for the demo |
| Submit student feedback on content | ✅ | Useful demo signal; reset nightly |
| **Upload XLSX / JSON to trigger pipeline build** | ❌ | Real LLM spend; demo can't initiate paid pipeline jobs |
| **Submit a curriculum definition (Phase D)** | ❌ | Same — would queue a paid build |
| **Adopt / import an OOB curriculum into library (Epic 12)** | ❌ | Library is pre-seeded with Grade 11 Science (§6); nothing to import |
| **Trigger backup / restore (Epic 15)** | ❌ | Expensive + cross-school visibility |
| **Provision new teachers / students** | ❌ | Modifies school roster; nightly reset would orphan accounts |
| **Stripe / billing actions** | ❌ | Demo has no card on file |

### Enforcement — UI hide + API guard

UI-only hiding is **not enough**. A curious evaluator hitting the API
directly (curl, browser devtools) would otherwise be able to burn
pipeline spend or queue a paid build. Two layers, both required:

| Layer | What it does |
|---|---|
| **Schema** | Add `is_demo BOOLEAN NOT NULL DEFAULT FALSE` to `teachers` and `students`. The seed script (§6) sets it `TRUE` for `demo-teacher@studybuddy.app` and `demo-student@studybuddy.app`. JWTs minted for these accounts include `is_demo: true` in the payload. |
| **API guard** | A FastAPI dependency `block_if_demo` that returns **403 + `{"error": "demo_account_readonly"}`** on the blocked endpoints. Applied via `Depends(block_if_demo)` on the routers in the blocked list above. |
| **UI hide** | When `is_demo` is true on the decoded JWT, hide the upload / import / definition-submit / provision / backup / billing buttons. Avoids the user clicking something that's just going to 403. |

Email-pattern matching (`email LIKE 'demo-%@studybuddy.app'`) was
considered and rejected — `is_demo` is a single column, survives any
future renaming, and is faster to check on the hot path.

### What the nightly reset has to undo

The §9 cron now also reverts:

- Any content overrides created or approved by `demo-teacher@` (back to seed baseline).
- Any annotations left on review drafts.
- Any feedback rows submitted by `demo-student@`.

Same idempotent re-run of `seed_demo_milfordwaterford.py` does it — no
new cron needed, just a wider reset scope captured in §9.

## 7 · Email templates (Zoho SMTP — already wired)

### 7.1 Confirm your email (sent on `POST /demo/request`)

```
From:    StudyBuddy Demo <demo@studybuddy.app>
Subject: Confirm your email to start your StudyBuddy demo

Hi {{name}},

You requested a 7-day demo of StudyBuddy. Click below to confirm your
email — your teacher and student login links will arrive right after.

  Confirm my email →
  https://demo.studybuddy.app/demo/confirm?token={{verify_token}}

This link is single-use and expires in 24 hours.
If you didn't request a demo, you can safely ignore this email — no
account is created until you confirm.

— The StudyBuddy team
demo@studybuddy.app
```

### 7.2 Your demo credentials (sent on `GET /demo/confirm`)

```
From:    StudyBuddy Demo <demo@studybuddy.app>
Subject: Your StudyBuddy demo is ready — 7-day access starts now

Hi {{name}},

Your demo is live until {{expiry}} ({{days_remaining}} days).

StudyBuddy has two views — teacher and student — and we've sent you a
direct link for each. No password to remember; just click the link.

────────────────────────────────────────────────────────────
  1. TEACHER VIEW   (start here — this is what schools buy)
────────────────────────────────────────────────────────────
  https://demo.studybuddy.app/school/login?demo_token={{teacher_token}}

  What you'll see:
    • Class roster for a sample Grade 11 classroom
    • Weekly digest and "students at risk" list
    • Lesson library and assignment view

────────────────────────────────────────────────────────────
  2. STUDENT VIEW   (what a Grade 11 student sees)
────────────────────────────────────────────────────────────
  https://demo.studybuddy.app/login?demo_token={{student_token}}

  What you'll see:
    • Lesson player, quiz, and tutorial
    • Progress dashboard and streak

────────────────────────────────────────────────────────────

A few things to know:

  • Bookmark these links. They work for the full 7 days — click as
    often as you like.

  • These are SHARED demo accounts. Other evaluators may be signed
    in at the same time, so please don't enter anything private —
    you may briefly see their activity, and they may see yours.

  • Access expires on {{expiry}} automatically. Nothing to cancel.

  • For a private or school-branded trial, reach out to
    sales@studybuddy.app — happy to set one up.

Questions or feedback? Reply directly to this email — it goes to a
real person.

— The StudyBuddy team
demo@studybuddy.app
```

The "shared demo account" disclosure is **load-bearing** — it sets
correct user expectations and removes any privacy claim against any
state another concurrent user might briefly see.

## 8 · Rate limiting — 20/day cap + abuse guards

Daily cap (one counter, since 20 is a global limit):

```python
def check_daily_cap():
    today_count = db.scalar(
        "SELECT COUNT(*) FROM demo_request "
        "WHERE created_at >= date_trunc('day', NOW() AT TIME ZONE 'UTC')"
    )
    if today_count >= 20:
        raise HTTPException(429, "Daily demo request limit reached. "
                                  "Try again tomorrow.")
```

Plus three per-key abuse limits (Redis-backed, already in stack):

| Key | Window | Cap | Why |
|---|---|---|---|
| `email` | 24 h | 1 | One person can't spam-request to refresh their own 7-day clock |
| `request_ip` | 1 h | 3 | One actor can't burn the daily 20 from a single IP |
| `request_ip` | 24 h | 5 | Same, longer window |

Plus a **Cloudflare Turnstile** widget on the form (free, no friction)
to filter automated requests before they reach the API.

## 9 · Cron jobs

| Cadence | Task | Reason |
|---|---|---|
| Hourly | Mark `pending_email` rows as `expired` once `verify_expires_at < NOW()` | Keeps status field truthful for the audit dashboard |
| Hourly | Mark `confirmed` rows as `expired` once `credentials_expires_at < NOW()` | Same |
| Nightly 03:00 UTC | Reset `demo-teacher` + `demo-student` accounts to seed-script baseline (revoke any pending edits, reset quiz attempts, reset progress, reset entitlements, **revert any content overrides created or approved during the day, drop annotations on review drafts, drop demo-student feedback rows** — see §6.5) | Keeps each new evaluation session starting from a clean state |

The hourly status sweeper is cheap (small table, indexed on
`*_expires_at`). The nightly account reset is the same pattern as
`scripts/demo/seed.sh` — idempotent re-run.

## 10 · Security / abuse hardening

| Concern | Mitigation |
|---|---|
| Email enumeration via the request endpoint | Always respond `202 Accepted` regardless of whether the email already has a pending/active request. The actual outcome lands in their inbox or doesn't. |
| Bots flood the daily 20 | `request_ip` rate limits (§8) + Cloudflare Turnstile on the `/demo` form |
| Stolen token URL | DB-backed status field allows targeted revocation; one SQL UPDATE per row |
| Demo accounts vandalized | Nightly cron (§9) resets shared accounts to seed baseline |
| Email goes to spam | Already covered by launch plan's SPF/DKIM/DMARC at `studybuddy.app` |
| Tokens leak via `Referer` header | Add `Referrer-Policy: no-referrer` to login redirect responses |
| Verify-link replay | `verify_token` is single-use — first hit flips status to `confirmed` and clears the token field |

## 11 · Frontend surface

Three small Next.js pages, all inside the `demo.studybuddy.app` deployment:

- **`/demo`** — `<DemoRequestForm>`: name input, email input, Cloudflare Turnstile widget, submit button → `POST /api/v1/demo/request`
- **`/demo/thanks`** — "Check your inbox" confirmation screen (after form submit)
- **`/demo/confirmed`** — landing page after the visitor clicks the verify link; shows "Credentials sent — check your inbox"

The two **login URLs** (`/school/login`, `/login`) are the existing
canonical login pages — no new frontend code is added there. The auth
middleware (§3.5) intercepts before the page renders when `demo_token`
is present and 302s straight to the relevant dashboard, so the demo
visitor never sees the login form.

## 12 · Operator surface (optional, recommended)

Single admin page at `/admin/demo-requests` listing recent requests with:

- name · email · status · created_at · use_count · last_used_at
- Per-row actions: **Revoke** (sets `status='revoked'`), **Resend credentials**

Good signal for "is anyone actually evaluating", and it's the kill-switch
for abuse. Likely worth ~30 min to add since the underlying table is
trivial to query.

## 13 · What's already in place vs. what to build

| Already there | Needs to be built |
|---|---|
| Zoho SMTP wired in `.env.demo` | 2 new API endpoints (`POST /demo/request`, `GET /demo/confirm`) |
| Redis for rate limiting | Auth-middleware extension on canonical `/school/login` + `/login` routes (~30 lines each) |
| Auth0 + JWT session machinery | New `demo_request` table + Alembic migration |
| MilfordWaterford school seed | Two new email templates |
| Production SMTP libs | Three small Next.js pages (`/demo`, `/demo/thanks`, `/demo/confirmed`) |
| Canonical `/school/login` and `/login` pages (no frontend changes needed) | Two new shared accounts in `seed_demo_milfordwaterford.py` |
| | `is_demo BOOLEAN` column on `teachers` + `students` (Alembic migration) |
| | `block_if_demo` FastAPI dependency + apply to blocked endpoints (§6.5) |
| | UI conditional hides on demo write surfaces (upload / import / definition / provision / backup / billing) |
| | Pre-adopt `default-2026-g11-science` into MilfordWaterford library in seed script |
| | Hourly cleanup cron (`demo_request` expiry sweeper) |
| | Nightly cron (shared-account state reset — wider scope per §6.5) |
| | Cloudflare Turnstile widget (5 min) |
| | (Optional) `/admin/demo-requests` audit page |

**Total surface:** ~1 small FastAPI router (2 routes), 1 auth-middleware
addition, 1 new table + 1 column on each of `teachers` / `students`,
1 `block_if_demo` dependency, 2 email templates, 3 small Next.js pages,
a handful of UI conditional-hides, 2 cron tasks, 1 seed update (now
including pre-adoption of the Grade 11 Science curriculum). Estimated
**2–3 days** of focused implementation (was 1–2 before §6.5). The
canonical-route approach (§3.5) keeps the public URL surface unchanged
and the long-term maintenance footprint minimal.

## 14 · Out of scope

- "Extend my demo" path (clicked link that bumps `credentials_expires_at`
  by another 7 days) — possible later add, not in this design
- Per-user data namespacing (every evaluator sees a private slice of
  the shared account's state) — possible later refinement if abuse
  becomes a problem
- Multi-language demo (Tamil, etc.) — the demo flow itself stays
  English-only at launch
- Pool of pre-created accounts (Pattern C from the original design
  conversation) — rejected in favor of shared accounts because the
  audience size doesn't justify the pool plumbing

## 15 · Open implementation choices

These can be deferred to implementation time but are flagged here so they
don't surface as surprises:

1. **Form location.** Likely `https://demo.studybuddy.app/demo`
   (subpath of the demo site, keeps everything in demo-environment scope).
2. **Cron cadence for shared-account reset.** Nightly 03:00 UTC chosen
   above; revisit if traffic patterns suggest finer granularity.
3. **Verify-link expiry.** 24 hours chosen above; reasonable default.
   Tighten to 4 hours if abuse signals appear.
4. **Audit dashboard scope.** §12 above — minimal version. If abuse
   becomes real, add filters for `status` and date range.
5. **Whether to log the visitor's IP geolocation** for analytics. Lean
   no — privacy posture is "we know your email and that's it".

## Change Log

| Date | Version | Change |
|---|---|---|
| 2026-05-09 | 0.1 | Initial design — flow, data model, endpoints, emails, abuse posture, cron schedule. Marked draft; not yet implemented. |
| 2026-05-09 | 0.2 | Reused canonical login routes (`/school/login`, `/login`) instead of dedicated `/demo/{teacher,student}/login` paths. Demo-token handling moves to auth middleware on the existing routes; no new public URL paths for login. New §3.5 captures the rationale and the wrong-link handling story. Updated §3 flow, §5 endpoints, §7 email template, §11 frontend surface, §13 build inventory. Driven by the long-term framing: `demo.studybuddy.app` is permanent, so the URL schema needs to age well. |
| 2026-05-09 | 0.3 | §6 made concrete — picked `Grade 11 — Science` (curriculum `default-2026-g11-science`, classroom led by Linda Ronstad) as the data anchor. Two new shared accounts to add to `seed_demo_milfordwaterford.py`: `demo-teacher@studybuddy.app` (co-teacher with Linda) and `demo-student@studybuddy.app` (third student alongside Fatima Al-Hassan and Liam O'Brien). Self-service evaluators see populated class data; named personas stay reserved for sales walkthroughs. |
| 2026-05-10 | 0.4 | §7.1 + §7.2 email templates rewritten for evaluator clarity — numbered teacher-first/student-second views with explicit "what you'll see" sub-bullets, expiry promoted to top of credentials email with `{{days_remaining}}` token, shared-accounts disclosure made concrete ("you may briefly see their activity, and they may see yours"), confirmation email now states "no account is created until you confirm." Private/school-branded-trial CTA routes to `sales@studybuddy.app` (was: reply to `demo@`). §3.5 cleaned up: dropped the "(or whatever the canonical student-login route is)" hedge — `/login` confirmed as the canonical student route at `web/app/(public)/login/page.tsx`. |
| 2026-05-10 | 0.5 | New §6.5 codifies demo-account write scope. Demo teacher is **read-mostly**: pipeline upload, curriculum-definition submit (Phase D), library import/adopt (Epic 12), backup/restore (Epic 15), teacher/student provisioning, and Stripe/billing actions are blocked. Content review (draft annotations, approve/reject/publish overrides) **is allowed** — in-flight reviews are intentionally trashed by the nightly reset. Enforcement: `is_demo BOOLEAN` column on `teachers` + `students`, `block_if_demo` FastAPI dependency returning 403, plus UI conditional-hides. Library is pre-seeded with `default-2026-g11-science` adopted into MilfordWaterford's library so the teacher sees a populated library on first login. §6 "what an evaluator sees" + §9 nightly reset scope + §13 build inventory all updated. Effort estimate raised to 2–3 days. |
