# Epic 7 — Self-Serve Demo System

**Status:** ✅ Complete

---

## What it is

A global, self-serve demo system that lets anyone — school administrators,
teachers, district buyers, or investors — request a pre-seeded demo environment
from the public website. The demo has a 24-hour TTL, is controlled by a
Platform Administrator [PLAT-ADMIN] role, and is geo-lockable by region.

This is distinct from the existing demo teacher/student accounts (which are
permanent fixtures). This epic creates on-demand, time-boxed, isolated demo
environments that expire automatically.

---

## Decisions captured from your notes

| # | Decision |
|---|---|
| 1 | PLAT-ADMIN can geo-lock demo access by region (restrict which countries/regions can request a demo) |
| 2 | A demo request triggers preparation of a "data package" delivered to the requester; the package is valid for **24 hours** by default |
| 3 | PLAT-ADMIN can extend a specific demo's validity beyond the 24-hour window |
| 4 | A requester is limited to **10 demo requests** lifetime |
| 5 | A requester can have **at most 1 active demo** at any time (no concurrent active requests) |
| 6 | Demo request metadata is tracked (who, when, from where); **no tracking of what the user does inside the demo** |

---

## Clarifying questions

These need answers before the spec can be finalised. Add your responses in the
**Your decisions / notes** section below.

### The "data package" — what does it contain?

**Option A — Live sandbox environment:**
The system provisions a running demo school (pre-seeded with teachers, students,
classrooms, curriculum, and realistic progress data) and sends the requester
login credentials. They log in to the real portal and explore a live, isolated
instance. Expires after 24h — credentials stop working.

**Option B — Downloadable dataset:**
The system sends a zip/JSON export that the requester imports into their own
environment. Requires technical setup on their end — less likely for a
non-technical school buyer.

**Option C — Guided read-only tour:**
An interactive walkthrough (similar to the pre-auth tours already built) but
with real-looking data. No live backend needed. The "package" is a personalised
URL with pre-filled data.

→ **Which option, or a combination?**
Option C seems like a low maintanence opetion in terms of data handling and housekeep chores.


---

### Geo-lock — what does it control?

**Option A — Block by IP country:**
Demo requests from certain countries are blocked outright at the API gateway.
Simple but easily bypassed with a VPN. Used for compliance or market focus.

**Option B — Regional capacity allocation:**
PLAT-ADMIN sets a quota per region (e.g. "max 50 active demos in West Africa,
20 in Europe"). New requests are accepted until the regional quota is full, then
queued or rejected with a "high demand" message.

**Option C — Whitelist mode:**
Demos are disabled globally by default. PLAT-ADMIN enables specific regions or
approves individual requests manually.

→ **Which option? And is geo-lock the default state (all locked, some opened) or
the exception (all open, some locked)?**

Option A seems more practical
---

### Who can request a demo?

**Option A — Fully public (no prior contact required):**
Anyone who visits the landing page can click "Request a demo", fill in name +
email + school/organisation, and receive a demo package. No vetting.

**Option B — Gated by email domain:**
Only requests from recognised school/education email domains are auto-approved.
Other domains go into a PLAT-ADMIN approval queue.

**Option C — Sales-qualified only:**
The "Request a demo" form submits a lead. PLAT-ADMIN reviews and manually
triggers the demo package for qualified prospects only.

→ **Which option?**
Option C works for me,
---

### The 10-request limit — how is a "requester" identified?

Email address only, or email + device fingerprint? Email is easy to bypass
(new email = new identity). If the limit matters for abuse prevention, a
stricter signal is needed.

→ **Email only, or stricter?**
email address only.
---

### What does the PLAT-ADMIN console look like?

At minimum: a list of active demo requests (requester, region, requested at,
expires at, status), controls to extend TTL or revoke early, and a geo-lock
configuration screen.

→ **Any additional controls needed?**
No additional controls required at this time.
---

## Decisions (finalised)

| Decision | Choice |
|---|---|
| Data package | **Option C** — Guided read-only tour with personalised URL (`?demo_token=`) |
| Geo-lock | **Option A** — Block by IP country via `CF-IPCountry` / `X-Country-Code` header |
| Who can request | **Option C** — Sales-qualified only; PLAT-ADMIN manually approves each lead |
| Requester identity | Email address only |
| PLAT-ADMIN console | Baseline: lead list, approve/reject, geo-block CRUD |

## What was built

| Phase | Status | What was built |
|---|---|---|
| L-1 | ✅ | Migration 0042: `demo_leads` + `demo_geo_blocks` tables; `plat_admin` ENUM added to `admin_role`; `demo:manage` permission in `permissions.py`; `DEMO_TOKEN_SECRET` / `DEMO_LEAD_TOKEN_TTL_HOURS` / `DEMO_LEAD_LIFETIME_MAX` / `DEMO_LEAD_ACTIVE_MAX` settings |
| L-2 | ✅ | `POST /demo/request` (public, slowapi 3/hour, geo-check, 1-active limit, lifetime limit); `src/demo_leads/` module (schemas, service, router); registered in app_factory |
| L-3 | ✅ | `POST /admin/demo-leads/{id}/approve` — generates HS256 JWT demo_token, stores in DB, sends approval email via `send_demo_approval_email()` with all 3 personalised tour URLs |
| L-4 | N/A | No seed script or Celery TTL task needed (Option C is stateless — token TTL embedded in JWT) |
| L-5 | ✅ | Admin console: `/admin/demo-leads` (lead list, approve/reject panels, TTL selector, tour URL display); `/admin/demo-settings` (geo-block CRUD); API client functions in `web/lib/api/admin.ts`; `plat_admin` role added to `useAdmin.ts` hook and `AdminNav.tsx` |
| L-6 | ✅ | `DemoTourBanner` component shown on all 3 tour pages (`/tour/school-admin`, `/tour/teacher`, `/tour/student`) when `?demo_token=` is present; banner decodes JWT client-side and greets by name and school |

## Tests

`backend/tests/test_demo_leads.py` — 15 tests (DML-01 … DML-15)  
Covers: request happy path, geo-block rejection, active-demo conflict, field validation,  
admin auth gate, lead listing and status filter, approve/reject flows, geo-block CRUD.

---

## Dependencies

- **Epic 2 (Production Launch)** — a deployed environment is needed to provision live demo sandboxes. Option A (live sandbox) cannot be built until a staging/production deployment exists.
- If Option C (guided tour / personalised URL) is chosen instead, Epic 2 is not a blocker — it can be built and deployed independently.

---

## Your decisions / notes

> Answer the clarifying questions above here. Even rough bullet points are enough.

**Data package (Option A / B / C):**
-

**Geo-lock model (Option A / B / C, default state):**
-

**Who can request (Option A / B / C):**
-

**Requester identity for the 10-request limit:**
-

**PLAT-ADMIN console — additional controls:**
-

**Anything else:**
-
