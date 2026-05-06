# Epic 15 — School Curriculum Backup & Restore

**Status:** ✅ Go — spec locked; ready to build BR-1 through BR-6

---

## Problem Statement

Schools accumulate custom curriculum content (adopted curricula, teacher overrides, unit
versions). A bulk regeneration, accidental deletion, or bad pipeline run can wipe that work.
A backup/restore system gives super-admins a safe recovery path without manual DB surgery,
driven by a school-initiated request workflow so accountability always stays with the school.

---

## Confirmed Requirements

| # | Requirement |
|---|---|
| BR-1 | Backups are scoped per school — one school's backup never touches another's data |
| BR-2 | Only super-admins can trigger or execute a restore; schools submit a *request* |
| BR-3 | Restore is selective: super-admin can target a specific **grade** or **curriculum name** |
| BR-4 | No partial content restores — minimum unit is a full curriculum (no topic/quiz granularity) |
| BR-5 | Backup covers DB rows **and** Content Store files together — they must travel as one unit |
| BR-6 | All backup/restore actions written to audit log — every step traceable |
| BR-7 | Backup/restore jobs run async (Celery) with a status endpoint |
| BR-8 | Dry-run / conflict detection before any restore commits |
| BR-9 | Backup manifest includes SHA-256 per file; integrity verified on restore before any writes |
| BR-10 | Conflicts → content restored to a **temp/staging catalog** for school to review and confirm override |
| BR-11 | Restore can be scheduled; duplicate requests for the same curriculum → only the most recent is kept; school notified of deduplication |
| BR-12 | Side-by-side restore supported — curriculum restored with versioned name `{name}.{yyyymmdd}` without touching the live curriculum |
| BR-13 | Retention: keep last **10 backups per school**; oldest pruned automatically when 11th is created |
| BR-14 | Backup schedule: configurable per school (default nightly); manual trigger also available |
| BR-15 | Notification: email sent to super-admin and school contact on job completion or failure |
| BR-16 | Status page: super-admin sees all schools' backup jobs; school admins see only their own |
| BR-17 | School portal: read-only backup history page + restore request submission form |
| BR-18 | Backup storage: separate S3 bucket in cloud (supports DR isolation), local folder for dev; `curriculum_backups` DB table holds metadata + file pointer |
| BR-19 | Cross-school restore: **not** supported for now — same-school only |

---

## ✅ Q6 Resolved — Backup Scope: Curriculum Only

Backup and restore covers **curriculum content only**. Student/teacher rosters, class
mappings, and progress records are explicitly excluded — no PII in backup archives.

**In scope:**

| Data | Tables / Store |
|---|---|
| Curricula metadata | `curricula` |
| Curriculum units | `curriculum_units` |
| Content versions | `content_subject_versions` |
| Content files | Content Store (lesson JSON, quiz JSON, MP3) |
| School LLM config | `school_llm_config` |
| Adopted platform curricula | `school_adopted_curricula` |
| Stream codes on curricula | `curricula.stream_code` |
| Classroom → curriculum package mappings | `classroom_packages` (no student data) |

**Out of scope (never backed up):**

| Data | Reason |
|---|---|
| Student roster (`students`) | PII — GDPR/FERPA obligation |
| Teacher roster (`teachers`) | PII — GDPR obligation |
| Student progress (`progress_sessions`, `student_answers`) | Educational records — FERPA |
| Classroom → student mappings (`classroom_students`) | Student PII |
| Student → teacher assignments (`student_teacher_assignments`) | Student PII |
| Stream on students/teachers (`students.stream`, `teachers.stream`) | Derived from roster |

---

## Decisions Log

| Q | Decision |
|---|---|
| Storage | Separate S3 bucket (cloud); local folder (dev). `curriculum_backups` table stores metadata + S3 path |
| Cross-school restore | No — same-school only |
| Conflict policy | Overwrite always, but conflicts first go to a temp/staging catalog; school must confirm override before live curriculum is replaced |
| Modified-content notification | If source content has been modified since backup, school is notified and must explicitly approve the override |
| Active-enrolment responsibility | School is responsible for managing enrolments; super-admin is not blocked but school is notified |
| Side-by-side restore | Restore to `{name}.{yyyymmdd}` versioned catalog; if that version exists it is overwritten |
| Duplicate restore requests | Only most recent request retained; school notified of deduplication |
| Retention | Last 10 backups per school; oldest pruned on creation of 11th |
| Trigger | Both: configurable schedule per school + manual on-demand |
| Notifications | Email to super-admin + school contact on completion/failure |
| Status visibility | Dedicated status page; super-admin = all schools; school admin = own school only |
| School visibility | Read-only backup history in school portal; school can submit restore requests |
| Audit | Full audit log page for backup/restore events — every step traceable |

---

## Phased Implementation Plan

### Phase BR-1 — DB + Storage Foundation
**Deliverables:** migrations, storage abstraction, no API yet

- Migration `0052`: `curriculum_backups` table
  ```
  id UUID PK, school_id FK, label TEXT, scope_type (grade|name|full),
  scope_value TEXT, storage_path TEXT, manifest_json JSONB,
  status (pending|running|completed|failed), backup_tier (curriculum|full),
  triggered_by UUID (admin_id), created_at TIMESTAMPTZ, expires_at TIMESTAMPTZ,
  file_count INT, total_bytes BIGINT
  ```
- Migration `0053`: `backup_restore_requests` table
  ```
  id UUID PK, school_id FK, backup_id FK, requested_by UUID (teacher/admin),
  status (submitted|acknowledged|dry_run|awaiting_school_confirm|in_progress|completed|cancelled),
  scope_type, scope_value, conflict_catalog_id UUID nullable,
  scheduled_at TIMESTAMPTZ nullable, notes TEXT,
  created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ
  ```
- `src/backup/storage.py` — `BackupStorage` ABC with `S3BackupStorage` + `LocalBackupStorage` implementations
- RLS on both tables (school_id isolation)

---

### Phase BR-2 — Backup Celery Job
**Deliverables:** backup task, manifest, retention pruning, scheduled trigger

- `src/backup/tasks.py`: `backup_school_task(school_id, scope_type, scope_value)`
  - Exports DB rows (curricula, curriculum_units, content_subject_versions, school_llm_config, school_adopted_curricula, classroom_packages, curricula.stream_code) to JSON
  - Copies Content Store files for the scoped curricula
  - Writes manifest with SHA-256 per file + DB row checksums
  - Uploads archive to S3 (or writes to local folder)
  - Creates `curriculum_backups` row on completion
  - Fires audit event `curriculum.backup_created`
- Retention pruning: after insert, delete oldest if school now has > 10 backups (delete DB row + S3 object)
- Celery Beat: per-school cron entry; configurable schedule stored in `school_llm_config` or a new `school_backup_config` column

---

### Phase BR-3 — Restore Workflow
**Deliverables:** request → dry-run → temp catalog → school confirm → final restore

- `src/backup/service.py`: restore state machine
  1. `submit_restore_request` — school submits; deduplication check (cancel prior pending for same curriculum)
  2. `acknowledge_request` — super-admin acknowledges; triggers dry-run
  3. `dry_run_restore` — detects conflicts (units modified since backup); creates temp staging catalog if conflicts exist; emails school + super-admin with conflict report
  4. `school_confirms_override` — school approves via school portal
  5. `execute_restore` — verifies SHA-256 manifest; writes DB rows + Content Store files; overwrites live curriculum
  6. Side-by-side path: if school requests versioned restore, target catalog name = `{name}.{yyyymmdd}`
- Audit events at every state transition: `restore.submitted`, `restore.dry_run_complete`, `restore.conflict_detected`, `restore.school_confirmed`, `restore.completed`, `restore.failed`

---

### Phase BR-4 — API Endpoints
**Deliverables:** REST surface for admin console + school portal

| Method | Path | Who | Purpose |
|---|---|---|---|
| `POST` | `/admin/schools/{id}/backups` | super-admin | Trigger manual backup |
| `GET` | `/admin/schools/{id}/backups` | super-admin | List backups for a school |
| `GET` | `/admin/backups` | super-admin | All schools' backup jobs |
| `GET` | `/admin/backups/{backup_id}` | super-admin | Backup detail + manifest |
| `POST` | `/admin/backups/{backup_id}/restore` | super-admin | Initiate restore from a backup |
| `GET` | `/admin/restore-requests` | super-admin | All pending restore requests |
| `PATCH` | `/admin/restore-requests/{id}/acknowledge` | super-admin | Acknowledge + trigger dry-run |
| `PATCH` | `/admin/restore-requests/{id}/execute` | super-admin | Execute after school confirms |
| `POST` | `/schools/{id}/restore-requests` | school admin | Submit a restore request |
| `GET` | `/schools/{id}/restore-requests` | school admin | List own restore requests |
| `GET` | `/schools/{id}/backups` | school admin | Read-only backup history |
| `PATCH` | `/schools/{id}/restore-requests/{rid}/confirm` | school admin | Confirm override after dry-run |
| `GET` | `/admin/backup-schedules` | super-admin | View/edit per-school schedules |
| `PUT` | `/admin/backup-schedules/{school_id}` | super-admin | Set schedule (cron expression) |

---

### Phase BR-5 — Admin UI
**Deliverables:** admin console pages

- `/admin/backups` — all schools' backup jobs table (school, scope, status, size, date, actions)
- `/admin/backups/[school_id]` — per-school backup list + "Create backup" button
- `/admin/restore-requests` — pending restore requests queue
- `/admin/restore-requests/[id]` — request detail + dry-run conflict report + Execute / Cancel actions
- `/admin/backup-schedules` — per-school schedule configurator

---

### Phase BR-6 — School Portal UI
**Deliverables:** school portal pages

- `/school/backups` — read-only list of this school's backups (date, scope, status, size)
- `/school/restore-requests` — list of submitted restore requests + current status
- `/school/restore-requests/new` — submit a restore request (pick backup → scope → notes)
- `/school/restore-requests/[id]/confirm` — review dry-run conflict report and confirm/reject override

---

## Notifications Spec

| Event | Recipient | Channel |
|---|---|---|
| Backup completed | Super-admin | Email |
| Backup failed | Super-admin | Email |
| Restore request submitted | Super-admin | Email |
| Dry-run complete with conflicts | School contact + Super-admin | Email |
| School confirmed override | Super-admin | Email |
| Restore completed | School contact + Super-admin | Email |
| Restore failed | School contact + Super-admin | Email |
| Duplicate request deduplicated | School contact | Email |

---

## Out of Scope (v1)

- Cross-school restore (clone school A → school B)
- Student/teacher roster backup (`students`, `teachers` — PII, GDPR/FERPA)
- Student progress backup (`progress_sessions`, `student_answers` — FERPA educational records)
- Classroom → student mappings (`classroom_students`, `student_teacher_assignments`)
- Student-initiated restore requests
- Backup download by school admin
- Incremental backups (full snapshot only for v1)
