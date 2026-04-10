# Design — Lesson Retention Service

> **Status:** Decisions complete — ready to ticket  
> **Author:** Sivakumar Mambakkam  
> **Last updated:** 2026-04-07  
>
> All design decisions are settled. This document is the source of truth
> for implementation. Refer to Section 11 for the phased build plan.

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

### Version cap — DECIDED

A school may hold up to **5 versions** of the same curriculum simultaneously.

**Enforcement:** When a school attempts to generate a 6th version, the system
blocks the action and prompts the admin to **completely remove** an existing
version first. There is no archive concept — removal is permanent (subject to
the 180-day purge grace on expired content).

**Counting rule:** All versions count toward the cap regardless of state
(active, expired, unavailable). A version must be fully purged or explicitly
deleted by the admin before the slot is freed.

---

## 4. Content Lifecycle

```
ACTIVE  (1 year from curriculum creation or last renewal)
    │
    │  30 days before expiry — pre-expiry warning email to school_admin
    │
    │  expiry date reached — no automatic renewal
    ▼
EXPIRED  → notification sent to school_admin
    │       content marked UNAVAILABLE (hidden from students immediately)
    │       files remain in content store during grace period
    │       version still counts toward the 5-version cap
    │
    │  180-day grace period
    │    • 90 days in  → reminder email
    │    • 30 days left → email + in-app alert
    ▼
PURGED  (files deleted from content store + CDN cache invalidated)
         version slot freed — no longer counts toward cap
```

### Lifecycle states

| State | Student sees content? | Files in store? | Admin can renew? | Counts toward cap? |
|---|---|---|---|---|
| ACTIVE | Yes | Yes | Yes | Yes |
| EXPIRED / UNAVAILABLE | No | Yes | Yes (during grace) | Yes |
| PURGED | No | No | No (must regenerate) | No |

### Student access on expiry — DECIDED

If a student is assigned to a version that expires, they **lose access
immediately**. There is no automatic fallback to another version. The admin
must reassign the grade to an active version via the retention dashboard.

---

## 5. Storage Model — DECIDED

### Included quota

Every school subscription includes **5 GB** of content storage as the base
allocation. This covers the majority of schools running a standard curriculum
across a few grades.

### Additional storage

Schools may purchase additional storage in **5 GB increments** via Stripe when
their usage approaches or exceeds the base quota.

### Metering

Storage usage is calculated from `payload_bytes` aggregated across all
`pipeline_jobs` for the school's curricula. The retention dashboard displays:

- Total storage used vs quota (e.g. 3.2 GB / 5 GB)
- Storage consumed per curriculum
- Storage consumed per version within each curriculum

This gives admins clear visibility before they decide to renew or remove a
version.

---

## 6. Cost Model — DECIDED

Two distinct billable events:

| Event | What it means | Cost |
|---|---|---|
| **Renew** | Extend expiry of existing content by 1 year — no regeneration | Storage charge only (based on quota tier) |
| **New version** | Run the AI pipeline to regenerate curriculum content | Anthropic token cost + storage of new content |

### Renewal billing

Renewal billing **starts from expiry date + 1 day** and runs for exactly
1 year. The admin is not charged from the day they click "Renew" — the new
period begins at the natural end of the old one, so no overlap or gap occurs.

### Anthropic cost tracking

Every pipeline run records the token cost (`tokens_used × cost_per_token`)
per curriculum per version. The **billing dashboard** presents this as a
statement:

| Curriculum | Grade | Version | Built On | Tokens Used | Est. Cost | Storage |
|---|---|---|---|---|---|---|
| Mathematics | 8 | v1 | Jan 2025 | 420,000 | $1.26 | 320 MB |
| Mathematics | 8 | v2 | Jun 2025 | 455,000 | $1.37 | 338 MB |
| Science | 8 | v1 | Jan 2025 | 510,000 | $1.53 | 410 MB |

Each version's cost is tracked and displayed separately so the admin has a
full audit trail of what was spent generating each version.

---

## 7. Notification Schedule — DECIDED

| Trigger | Channel | Recipient |
|---|---|---|
| 30 days before expiry | Email | school_admin |
| Expiry date reached | Email | school_admin |
| 90 days into grace period | Email | school_admin |
| 30 days before purge (day 150 of grace) | Email + in-app alert | school_admin |
| Purge completed | Email | school_admin |

Notifications go to `school_admin` only — teachers are not included in
retention alerts.

---

## 8. Version Assignment — DECIDED

Version assignment is **per grade**. When a school admin pins a version to
a grade, all students in that grade are served that curriculum version.

Assignment is managed in the retention dashboard. Granularity:

```
School → Grade → Curriculum version (v1–v5)
```

This maps cleanly to the existing grade-based enrolment model and keeps
the curriculum resolver simple: one active version per grade at any time.

---

## 9. Retention Panel (UI) — DECIDED

**Location:** Under `/school/subscription`

Accessible to `school_admin` only. Combines retention status, storage usage,
and Anthropic cost into a single view.

### Panel layout

**Storage summary strip** (top of panel)

```
[ 3.2 GB used of 5 GB ]  ████████░░░░░  64%   [ Buy more storage ]
```

**Curriculum retention table**

| Curriculum | Grade | Versions | Expires On | Status | Storage | Actions |
|---|---|---|---|---|---|---|
| Mathematics | 8 | 3 / 5 | Jan 2026 | Active | 1.1 GB | Renew / Details |
| Science | 8 | 2 / 5 | Mar 2026 | Expiring in 30d | 820 MB | Renew |
| History | 9 | 1 / 5 | Dec 2025 | Grace (120d left) | 640 MB | Renew / Remove |
| Art | 7 | 5 / 5 | Jun 2025 | Purged | — | Regenerate |

**Version detail drawer** (on "Details" click)

Shows per-version breakdown: built date, tokens used, est. cost, storage,
assigned grades, and individual remove action per version.

---

## 10. Compliance Notes

Non-negotiable — not subject to change:

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

## 11. All Decisions — Summary

| # | Decision | Resolution |
|---|---|---|
| 3a | Version cap enforcement | Block + prompt. Admin must fully remove a version before adding a new one. No archive. |
| 3b | Expired versions and the cap | All versions (any state) count toward the cap until purged or explicitly deleted. |
| 5a | Storage pricing | 5 GB base included in subscription; additional in 5 GB increments via Stripe; metered usage shown on dashboard. |
| 5b | Anthropic cost model | Track `tokens_used × cost_per_token` per pipeline run per version; display as per-curriculum billing statement. |
| 5c | Payment timing | Renewal billing starts from `expiry_date + 1 day` and runs 1 year — no overlap, no gap. |
| 6a | Version assignment granularity | Per grade. One active version per grade at a time. |
| 6b | Fallback on expiry | No fallback. Students lose access until admin reassigns the grade to an active version. |
| 7a | Pre-expiry notification | 30 days before expiry (in addition to notifications during grace period). |
| 8a | Retention panel location | Under `/school/subscription`. |

---

## 12. Implementation Phases

| Phase | Scope | Key deliverables |
|---|---|---|
| **A — Schema** | DB foundation | `curricula.status` column (active/expired/unavailable/purged); `curricula.expires_at`; `curriculum_versions.cost_usd`; `curriculum_versions.tokens_used`; `school_storage_quota` table (base + purchased GB) |
| **B — Version cap** | Enforcement | Block pipeline trigger if 5 versions exist; API returns structured error prompting admin to remove a version; version slot freed only on purge or explicit delete |
| **C — Storage metering** | Usage tracking | Aggregate `payload_bytes` per curriculum per version; expose `GET /school/storage` returning used/quota/breakdown; Stripe integration for 5 GB add-on packages |
| **D — Lifecycle jobs** | Celery Beat | Daily: detect expired curricula, mark unavailable, send expiry email; Day 90 of grace: reminder email; Day 150: email + in-app alert; Day 180: purge files from content store + CDN invalidation + free version slot |
| **E — Notifications** | Email templates | 5 templates: 30-day pre-expiry warning; expiry notification; 90-day grace reminder; 30-day-to-purge alert; purge confirmation |
| **F — API** | Endpoints | `GET /school/retention` (curriculum list with status); `POST /school/retention/{curriculum_id}/renew` (schedule renewal billing from expiry+1); `DELETE /school/retention/{version_id}` (explicit version remove); `PUT /school/grades/{grade}/curriculum-version` (version assignment per grade) |
| **G — Billing** | Stripe | Renewal subscription starting from `expiry_date + 1`; storage add-on packages; pipeline cost recorded per version (informational, not separately billed in v1) |
| **H — UI** | Retention panel | Storage summary strip; curriculum retention table; version detail drawer; grade version assignment selector; cost estimate modal before renew confirmation |
