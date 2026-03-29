# Phase W5 — School Portal (Admin + Curriculum) — PRE

**Date:** 2026-03-27
**Preceding phase:** W4 — School Portal Teacher Reporting (complete, 38 routes, 45 tests)
**Goal:** School admins can manage curriculum (XLSX upload + pipeline), student roster, teachers, and school settings.

---

## Scope

### Pages to build (all under `/school/*`)

| #    | Route                                  | Description                                                                      | Backend endpoint                                                    |
| ---- | -------------------------------------- | -------------------------------------------------------------------------------- | ------------------------------------------------------------------- |
| T-11 | `/school/curriculum`                   | Active curriculum card, XLSX upload form, trigger pipeline                       | `POST /curriculum/upload/xlsx`, `POST /curriculum/pipeline/trigger` |
| T-12 | `/school/curriculum/pipeline/[job_id]` | Real-time pipeline progress (5 s poll), unit-level status, error list            | `GET /curriculum/pipeline/{job_id}/status`                          |
| T-13 | `/school/students`                     | Enrolled student roster table; generate enrolment invite link; bulk email upload | `GET /schools/{id}/enrolment`, `POST /schools/{id}/enrolment`       |
| T-14 | `/school/teachers`                     | Teacher list; invite form; role dropdown; deactivate (school_admin only)         | `POST /schools/{id}/teachers/invite`                                |
| T-15 | `/school/settings`                     | School name, country, enrolment code display; billing portal link                | `GET /schools/{id}`, `GET /subscription/billing-portal`             |

### API modules to add

| Module                        | New exports                                                                            |
| ----------------------------- | -------------------------------------------------------------------------------------- |
| `lib/api/curriculum-admin.ts` | `uploadCurriculumXlsx`, `triggerPipeline`, `getPipelineStatus`, `downloadXlsxTemplate` |
| `lib/api/school-admin.ts`     | `getSchoolProfile`, `getRoster`, `uploadRoster`, `inviteTeacher`                       |

### Tests

| File                                 | Coverage                                                              |
| ------------------------------------ | --------------------------------------------------------------------- |
| `tests/unit/pipeline-poller.test.ts` | Poll logic: progress calc, done/failed detection, interval cleanup    |
| `tests/unit/xlsx-errors.test.ts`     | Per-row error list rendering; zero-error state; multiple-field errors |
| `tests/unit/invite-link.test.ts`     | Enrolment invite link construction from enrolment_code                |

---

## Key Design Decisions

### XLSX upload flow

1. User selects file via `<input type="file">` → `POST /curriculum/upload/xlsx` (multipart/form-data)
2. On success (201): `curriculum_id` returned → auto-trigger pipeline via `POST /curriculum/pipeline/trigger`
3. On error (400): `errors[]` array rendered as a per-row error table (row, field, message)
4. Pipeline job_id navigates to `/school/curriculum/pipeline/[job_id]`

### Pipeline poller

- Uses `useQuery` with `refetchInterval: 5000` (TanStack Query built-in)
- Refetch stops automatically when `status === "done"` or `"failed"` (set `refetchInterval` to `false`)
- Progress bar animates from `progress_pct` field
- Error list shows per-unit failures when `failed > 0`

### XLSX upload is `multipart/form-data`

The school-client axios instance needs `Content-Type: multipart/form-data` for the upload endpoint. Use `FormData` object directly — axios sets boundary automatically.

### Enrolment invite link

Backend returns `enrolment_code` in the school profile. The invite URL is constructed client-side: `${origin}/enrol/${enrolment_code}`. Copy-to-clipboard button provided.

### Roster upload

`POST /schools/{id}/enrolment` takes `{ student_emails: string[] }` JSON body. The UI provides a textarea for comma/newline-separated emails, parsed client-side before submission.

### Teacher invite (school_admin only)

`POST /schools/{id}/teachers/invite` takes `{ name, email }`. Newly invited teachers receive an Auth0 invitation email. The teacher list is derived from the school profile + any newly added teachers shown optimistically.

### Role enforcement (school_admin only pages)

T-14 and parts of T-15 are school_admin only. The `useTeacher` hook exposes `role`; pages conditionally render or redirect based on `teacher.role !== "school_admin"`.

---

## Exit Criteria

- XLSX upload form renders, submits, and shows per-row errors on 400 response
- Pipeline poller shows live progress with progress bar; stops when done/failed
- Student roster renders enrolled students; invite link copies to clipboard
- Teacher invite form submits and shows success
- School settings page shows profile data and billing portal link
- `npm run typecheck` passes
- `npm run build` succeeds (target: ≥ 43 routes)
- Unit tests pass (target: ≥ 55 total)
