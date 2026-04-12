# Epic 7 — Self-Serve Demo System

**Status:** 💭 Needs answers to clarifying questions below

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

---

### The 10-request limit — how is a "requester" identified?

Email address only, or email + device fingerprint? Email is easy to bypass
(new email = new identity). If the limit matters for abuse prevention, a
stricter signal is needed.

→ **Email only, or stricter?**

---

### What does the PLAT-ADMIN console look like?

At minimum: a list of active demo requests (requester, region, requested at,
expires at, status), controls to extend TTL or revoke early, and a geo-lock
configuration screen.

→ **Any additional controls needed?**

---

## Rough scope (assuming Option A for data package — live sandbox)

| Phase | What gets built |
|---|---|
| L-1 | `demo_requests` table + PLAT-ADMIN role + geo-lock config table |
| L-2 | Demo request API: `POST /demo/request` (rate-limited, geo-checked, throttled to 1 active); confirmation email with credentials |
| L-3 | Demo provisioning: seed script that creates an isolated demo school on request (teachers, students, classrooms, curriculum, progress data) |
| L-4 | TTL expiry: Celery Beat task that deactivates expired demo schools every hour; PLAT-ADMIN extend endpoint |
| L-5 | PLAT-ADMIN console: request list, extend/revoke controls, geo-lock settings, regional capacity view |
| L-6 | Public landing page: "Request a demo" form with region detection and queue messaging when at capacity |

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
