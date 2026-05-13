# Design — Content Versioning & Review Lifecycle

> **Status:** Problem statement / direction — pre-implementation
> **Author:** Sivakumar Mambakkam (concept), drafted 2026-05-11
> **Last updated:** 2026-05-11
>
> This document captures a design issue surfaced during demo testing and the
> related concerns the school-admin workflow needs to address before
> production. It is **not** an implementation spec — open questions remain.
> Convert to a phased plan once decisions are settled and graduate it to an
> Epic in `docs/epics/`.

---

## 1. The problem

The `content_subject_versions` table records one row per pipeline-generation
event for a given `(curriculum_id, subject)`. A Grade 11 Chemistry subject
with four regenerations has four rows: v1, v2, v3, v4.

What looks like four "versions" of the lesson content is actually **one** set
of lesson files. The content store layout is:

```
{CONTENT_STORE_PATH}/curricula/{curriculum_id}/{unit_id}/lesson_en.json
```

Note: keyed by `(curriculum_id, unit_id)`, **not** by `version_id`. Each
pipeline run overwrites the same files on disk. The version table grows by
one row; the content store stays at the latest snapshot.

### Implications

| Consequence | Today |
|---|---|
| Students always see the most recent regeneration | Yes — by accident, not by policy |
| Admin / school-admin can "review v2" before approving v3 | No — opening v2's review page renders v3's content |
| Roll back if a regeneration is worse than what it replaced | Not possible without re-running the pipeline |
| Diff page actually compares historical content snapshots | No — it diffs metadata + reviewer annotations |
| `status='published'` on multiple versions is consistent | All four say `published`, only one set of files exists |

The Content Library rollup UX shipped in 2026-05-11 (the "4 versions" badge
on a single subject row) is **technically accurate** in that only one set of
content can be served, but it papers over the underlying gap.

---

## 2. Why this matters before production

A real school admin will, at some point:

1. Have their AI provider regenerate a subject with a tweak to the prompt
2. Want to **preview** the new version before students see it
3. Want to **revert** if the regeneration introduced a regression
4. Want to **explain to a parent** what changed between dates

None of those workflows are possible today. The system silently replaces
content the moment the pipeline finishes; the human-in-the-loop review queue
is reviewing the same content it would have shown the student anyway.

---

## 3. Scope of work — the concerns

Concerns surfaced by the user (Sivakumar) plus the adjacent ones the
school-admin workflow needs to address. Each row is a sub-question that
may turn into its own ticket or decision.

| # | Concern | What needs deciding |
|---|---|---|
| 1 | **Per-version content storage** | Whether content files are written to versioned paths (`/v{N}/`) or stay overwrite-in-place with a separate snapshot mechanism. Storage cost, sync overhead, and CDN invalidation patterns are all affected. |
| 2 | **Review-before-accept workflow** | When a new version is generated, who sees it first? Today: students immediately. Proposed: school-admin (or platform-admin for platform curricula) approves → it becomes active. Question: per-subject, per-unit, or per-curriculum granularity? |
| 3 | **Removal of older versions** | After how long do we drop v2 files when v4 has been live for N days? Quota-driven? Time-driven (TTL)? Or kept forever as audit? |
| 4 | **Diff visibility** | What does "what changed between v3 and v4" actually show — text diff per section, summary of structural changes, or both? Today's diff page is annotation-only; section-text diff requires #1. |
| 5 | **Rollback** | Restoring v2 over v4: is that copy-files-back, or generate a new "v5 = identical to v2" entry to preserve the audit trail? |
| 6 | **Audit trail** | Who approved which version, when, with what notes. Today we have the `content_annotations` table for review notes — does it extend naturally? |
| 7 | **Teacher notification on regeneration** | When a subject is regenerated, do teachers who use that subject get an alert? Class continuity vs. content currency tension. |
| 8 | **School-fork-vs-platform-version interaction** | Epic 12 ships school overrides (`unit_content_overrides`). Need to specify: does platform v4 → v5 break the school's override? Do school overrides themselves get a version timeline? |
| 9 | **Cost / storage** | If we keep N versions per subject × M subjects × K curricula, storage costs scale linearly. Approximate sizing needed. |
| 10 | **CDN invalidation on version switch** | Today CloudFront is invalidated on content bump. With versioned URLs the invalidation surface shrinks but TTL strategy changes. |

---

## 4. Actors & responsibilities

Working assumption — confirm before locking in.

| Actor | What they can do | Why |
|---|---|---|
| Platform admin (`super_admin`) | Approve / reject new versions of **platform** curricula (`owner_type='platform'`) before they go live | Platform content reaches every school; one gate. |
| School admin | Approve / reject new versions of **school-owned** curricula (forks under `owner_type='school'`) AND choose whether their school adopts a new platform version when one becomes available | Insulates the school's classrooms from upstream regenerations they haven't vetted. |
| Teacher | Read-only on version history. Receives notification when "their" subject is updated. | Continuity for in-flight teaching. |
| Student | Always sees the active version. No visibility into versioning. | Versioning is an operator concern. |

The "school-admin approves new platform versions" piece is novel — today
platform regenerations propagate instantly. Adding this gate is the
highest-impact change for production readiness.

---

## 5. Proposed direction (sketch, not decided)

### 5.1 Content storage

Two candidate models:

**Option A — Versioned content paths**
```
curricula/{curriculum_id}/{unit_id}/v{N}/lesson_en.json
                                        meta.json
                                        ...
```
- Serving layer reads the "active" version from a pointer (per-school, per-subject — see 5.3)
- Each pipeline run writes to a new `vN` directory
- Rollback = flip the active pointer
- CDN URLs include version → infinite cache TTL, no invalidation needed on rollback

**Option B — Overwrite + snapshot**
- Active content stays at `curricula/{curriculum_id}/{unit_id}/`
- On generation, the previous content is snapshotted to `curricula/{curriculum_id}/{unit_id}/_history/v{N}/`
- Saves the "active path is canonical" mental model but doubles writes on every regen

Option A is cleaner and probably the right call; B is simpler to retrofit.

### 5.2 Approval state

Extend `content_subject_versions.status`. Proposed lifecycle:

```
generated  ──►  pending_review  ──►  approved  ──►  active
                                          │           ▲
                                          └── deactivate to roll back ────┘
                                          ↓
                                      archived
```

Today's `status='published'` collapses both "approved" and "active." Split them.

### 5.3 Active-pointer table

A new `content_active_version` table — per (school_id, curriculum_id, subject)
points to a single `version_id` that is currently served. Default is the
platform's most-recently-approved version; schools can pin to an older one
explicitly.

```sql
CREATE TABLE content_active_version (
  school_id      UUID NOT NULL,  -- nullable for platform default
  curriculum_id  TEXT NOT NULL,
  subject        TEXT NOT NULL,
  version_id     UUID NOT NULL REFERENCES content_subject_versions,
  activated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  activated_by   UUID,           -- admin / school_admin
  PRIMARY KEY (school_id, curriculum_id, subject)
);
```

This is also where the school-admin "I've reviewed and accept the new
platform version" decision lands.

### 5.4 Retention policy

Proposed default: keep the last **3 approved versions** + the currently-active
version, regardless of age. Drop older approved versions on a Celery Beat
sweeper. Operator can adjust per-curriculum.

Open question: should rejected / never-approved versions be kept at all?
Probably yes for a short audit window (30 days) then dropped.

---

## 6. Out of scope (explicitly)

- Per-unit versioning is too fine — version unit at the subject level (matches
  today's `content_subject_versions`).
- Streaming partial content (showing v4 for lesson, v3 for quiz) is a
  consistency nightmare; reject.
- Letting students opt into "old version" — confusing for parents and breaks
  progress continuity.

---

## 7. Open questions

1. **Who pays the storage cost** of keeping multiple versions per school?
   Platform absorbs, or factored into the subscription?
2. **Does the active-version pointer apply to school-owned curricula too**
   (Epic 12 forks)? The fork already has its own `unit_content_overrides` —
   integrating with this versioning model needs careful design.
3. **First-time adoption** of a curriculum: does the school admin need to
   approve the *initial* version, or is "platform-approved + school adopts" =
   automatically active?
4. **Notification fatigue:** how to bundle "23 subjects regenerated today"
   into a single school-admin digest rather than 23 emails.
5. **Read-while-rotating consistency:** mid-class student request lands during
   an active-pointer flip — what guarantees do we make?

---

## 8. Phasing (placeholder)

When this graduates to an Epic, suggested phasing:

| Phase | Deliverable |
|---|---|
| V-1 | Versioned content paths in the Content Store + pipeline writes there |
| V-2 | `content_active_version` table + serving-layer reads the pointer |
| V-3 | School-admin "review new platform version" UI + accept/reject |
| V-4 | Section-level diff (real content snapshot diff, not just annotations) |
| V-5 | Retention sweeper + audit notifications |
| V-6 | Cross-cutting: teacher notification on update, parent-facing change log |

---

## 9. Decisions log

Add entries here as decisions are made.

| Date | Decision | Rationale |
|---|---|---|
| _pending_ | _Option A vs B for storage_ | _to be decided after sizing pass_ |

---

## 10. Cross-references

- **CLAUDE.md** — "Content Store Layout" + "Content Review Workflow" sections
- **EPIC_10_curriculum_lifecycle.md** — covers archive at the *curriculum*
  level (1-year TTL on whole curricula); this design is at the *version*
  level inside a single curriculum
- **EPIC_12_teacher_content_authoring.md** — school fork model (school
  overrides individual units of a platform curriculum); needs reconciliation
  with the versioning model proposed here
- **EPIC_15_backup_restore.md** — backup is at the school level, not the
  version level; the two systems are complementary, not overlapping
