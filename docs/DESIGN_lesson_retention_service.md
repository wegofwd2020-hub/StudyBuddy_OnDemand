# Design — Lesson Retention Service

> **Status:** In design — decisions pending  
> **Author:** Sivakumar Mambakkam  
> **Last updated:** 2026-04-07  
>
> This document captures the design decisions for the Lesson Retention Service.
> Open items are marked **[ OPEN ]** — add thoughts directly in those sections
> before implementation is ticketed.

---

## 1. Concept

Schools, Independent Teachers, and Independent Students may choose to set a
retention period for their curriculum content. The default retention frame is
**1 year**. The account holder receives notifications as expiry approaches and
can choose to **renew** (extend retention) or **let the content expire**, in
which case it is removed from their catalog.

---

## 2. Actors

| Actor | Primary account holder | Who manages retention | Release |
|---|---|---|---|
| School | `school_admin` | `school_admin` only | First release |
| Independent Teacher | The teacher | Themselves | Depends on #57 |
| Independent Student | The student | Themselves | Depends on #57 |

> **Note:** Independent Teacher and Independent Student as standalone actors
> were removed in ADR-001 and are tracked in issue #57. The first release of
> this service is scoped to **Schools only**. Independent actors will follow
> once #57 lands.

---

## 3. Retention Scope

**The retention clock is per-curriculum — not per subject-version.**

A curriculum has one expiry date. Publishing a new version of a subject within
the same curriculum does **not** reset the clock.

### Version cap

A school may hold up to **5 versions** of the same curriculum simultaneously.

#### [ OPEN — Decision 3a ] Version cap enforcement

When a school attempts to generate a 6th version, the recommended behaviour
is to **block and prompt** the admin to retire an older version first, rather
than auto-retiring the oldest.

> **Your thoughts:**

#### [ OPEN — Decision 3b ] Expired versions and the cap

Does an expired or unavailable version count toward the 5-version cap,
or only active versions?

> **Your thoughts:**

---

## 4. Content Lifecycle

```
ACTIVE  (1 year from curriculum creation or last renewal)
    │
    │  expiry date reached — no automatic renewal
    ▼
EXPIRED  → notification sent to school_admin
    │       content marked UNAVAILABLE (hidden from students immediately)
    │       files remain in content store during grace period
    │
    │  180-day grace period
    ▼
PURGED  (files deleted from content store + CDN cache invalidated)
```

### Lifecycle states

| State | Student sees content? | Files in store? | Admin can renew? |
|---|---|---|---|
| ACTIVE | Yes | Yes | Yes |
| EXPIRED / UNAVAILABLE | No | Yes | Yes (during grace) |
| PURGED | No | No | No (must regenerate) |

---

## 5. Renewal vs New Version — Two Distinct Cost Events

| Event | What it means | What it costs |
|---|---|---|
| **Renew** | Extend expiry of existing content by 1 year — no regeneration | Storage space only |
| **New version** | Run the AI pipeline to generate fresh content | Anthropic token usage + storage of new content |

`payload_bytes` is already tracked on `pipeline_jobs` and can be aggregated
per curriculum to compute a storage cost estimate shown to the admin before
they confirm.

### [ OPEN — Decision 5a ] Storage pricing formula

At what rate is storage charged for renewal?

- $/GB/year flat rate?
- Metered against actual `payload_bytes`?
- Is a cost estimate shown to the admin before they confirm renewal?

> **Your thoughts:**

### [ OPEN — Decision 5b ] Anthropic cost tracking for new versions

The pipeline tracks `payload_bytes` but not USD cost directly.

Options:
- Track `tokens_used × cost_per_token` and invoice the school per new version
- Include new-version generation within the school subscription plan up to a quota (e.g. N pipeline runs/year included)
- Hybrid: first N versions/year included; additional versions billed per run

> **Your thoughts:**

### [ OPEN — Decision 5c ] Payment timing

When a school admin clicks "Renew":

- Charged immediately via Stripe (charge now), **or**
- Added to the next billing cycle?

> **Your thoughts:**

---

## 6. Version Assignment to Students

School admins can assign a specific version (v1–v5) of a curriculum to
students. Currently students are resolved to "the active curriculum for their
school." Version pinning is a new concept that affects the curriculum resolver
(`cur:{student_id}` Redis cache).

### [ OPEN — Decision 6a ] Assignment granularity

When pinning a version to students, is the assignment:

- Per **grade** (all Grade 8 students → v2)?
- Per **student** (individual override)?
- Per **subject** within a grade?

> **Your thoughts:**

### [ OPEN — Decision 6b ] Fallback on expiry

If a student is pinned to v2 and v2 expires:

- Fall back to the latest active version automatically?
- Lose access until the admin reassigns?
- Notify the admin and freeze access for N days before fallback kicks in?

> **Your thoughts:**

---

## 7. Notification Design

| Trigger | Channel | Recipient |
|---|---|---|
| Expiry date reached | Email | school_admin |
| 90 days into grace period | Email | school_admin |
| 30 days before purge | Email + in-app alert | school_admin |
| Purge completed | Email | school_admin |

### [ OPEN — Decision 7a ] Additional notification triggers

Should notifications also be sent:

- At 30 days *before* expiry (pre-expiry warning)?
- At 60 days before expiry?
- To teachers as well as school_admin?

> **Your thoughts:**

---

## 8. The Retention Panel (UI)

Accessible to `school_admin` only. Shows all curricula with their retention
status, expiry date, version count, and available actions.

### Sketch

| Curriculum | Grade | Versions | Active Since | Expires On | Status | Actions |
|---|---|---|---|---|---|---|
| Mathematics | 8 | 3 of 5 | Jan 2025 | Jan 2026 | Active | Renew / Details |
| Science | 8 | 2 of 5 | Mar 2025 | Mar 2026 | Expiring | Renew |
| History | 9 | 1 of 5 | Dec 2024 | Dec 2025 | Grace (120d left) | Renew / Remove |
| Art | 7 | 5 of 5 | Jun 2024 | Jun 2025 | Purged | Regenerate |

### [ OPEN — Decision 8a ] Panel location

Where does this panel live in the school admin UI?

- Under `/school/subscription`?
- A dedicated `/school/content-retention` route?
- Integrated into the existing `/school/curriculum` page?

> **Your thoughts:**

---

## 9. Compliance Notes

These are non-negotiable and not open for decision:

- **FERPA:** Student progress records (quiz scores, session history) are
  educational records. They must be retained independently of content expiry.
  Expiring a curriculum does **not** erase student progress data for units
  within that curriculum.
- **GDPR:** The 180-day purge grace period cannot be shortened below 30 days
  (aligns with existing account deletion schedule). The 180-day default
  provides comfortable headroom.
- **COPPA:** Retention management is an admin action. No COPPA-specific
  handling required for this service.

---

## 10. What Is Fully Decided (Ready to Ticket)

The following are confirmed and require no further input:

- [x] Retention clock is per **curriculum**, not per subject-version
- [x] Default: **manual renewal** — no auto-renew
- [x] Expiry → content immediately **unavailable** to students
- [x] **180-day grace period** before hard purge
- [x] Renewal restricted to **school_admin** only
- [x] **5-version cap** per curriculum
- [x] Two distinct cost events: **renew** (storage) vs **new version** (tokens + storage)
- [x] First release scoped to **Schools** — independent actors follow after #57
- [x] Student progress data is **never** deleted as part of content expiry

---

## 11. Implementation Phases (Outline — subject to decisions above)

| Phase | Scope |
|---|---|
| **Phase A** | Schema: `content_retention` table; version cap enforcement; lifecycle state column on `curricula` |
| **Phase B** | Celery Beat: expiry detection job; 180-day purge job; CDN invalidation on purge |
| **Phase C** | Notifications: email templates for all triggers |
| **Phase D** | API: `GET /retention`, `POST /retention/{id}/renew`, version assignment endpoints |
| **Phase E** | Web UI: retention panel; version assignment UI; cost estimate before renewal |
| **Phase F** | Stripe: storage-based renewal billing; pipeline cost tracking for new versions |

---

## 12. Open Decisions Summary

| # | Decision | Status |
|---|---|---|
| 3a | Version cap enforcement (block+prompt vs auto-retire) | **[ OPEN ]** |
| 3b | Do expired versions count toward the 5-version cap? | **[ OPEN ]** |
| 5a | Storage pricing formula | **[ OPEN ]** |
| 5b | Anthropic cost model for new versions | **[ OPEN ]** |
| 5c | Payment timing (immediate vs next billing cycle) | **[ OPEN ]** |
| 6a | Version assignment granularity (grade / student / subject) | **[ OPEN ]** |
| 6b | Fallback behaviour when pinned version expires | **[ OPEN ]** |
| 7a | Additional notification triggers (pre-expiry warnings) | **[ OPEN ]** |
| 8a | Retention panel location in the UI | **[ OPEN ]** |
