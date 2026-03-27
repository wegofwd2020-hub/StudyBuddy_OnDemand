# Phase W5 — School Portal (Admin + Curriculum) — POST

**Completed:** 2026-03-27
**Tests:** 76 passing (added 31 new — 13 pipeline + 10 XLSX errors + 10 invite/roster)
**Build:** Clean (43 routes, 0 type errors)

---

## Deliverables

### Routes added

| Route | Page | Req |
|---|---|---|
| `/school/curriculum` | XLSX upload form, template download, per-row error table, auto-trigger pipeline | T-11 |
| `/school/curriculum/pipeline/[job_id]` | Live pipeline progress bar (5 s poll via refetchInterval), done/failed states | T-12 |
| `/school/students` | Roster table, enrolment invite link + copy, bulk email upload textarea | T-13 |
| `/school/teachers` | Invite form (school_admin only), invited-this-session list, role badge | T-14 |
| `/school/settings` | School profile, enrolment code, billing portal button (admin only) | T-15 |

### API modules added

| Module | Exports |
|---|---|
| `lib/api/curriculum-admin.ts` | `uploadCurriculumXlsx`, `triggerPipeline`, `getPipelineStatus`, `downloadXlsxTemplate` |
| `lib/api/school-admin.ts` | `getSchoolProfile`, `getRoster`, `uploadRoster`, `inviteTeacher` |

### Tests added

| File | Tests | Coverage |
|---|---|---|
| `tests/unit/pipeline-poller.test.ts` | 13 | `getPipelineStatus`, progress_pct logic, poll-stop conditions, `triggerPipeline` |
| `tests/unit/xlsx-errors.test.ts` | 10 | Error grouping, row-0 file-level errors, zero-error success path, API mock |
| `tests/unit/invite-link.test.ts` | 10 | Invite URL construction, email parsing (newline/comma/semicolon), `inviteTeacher`, `uploadRoster` API mocks |

### SchoolNav updated

Added: Curriculum, Students, Teachers (admin-only), Settings nav items.
Teachers item is filtered by `teacher.role === "school_admin"`.

---

## Key Implementation Details

### XLSX upload flow
1. User selects file → `POST /curriculum/upload/xlsx?grade=N&year=Y&name=…` (multipart/form-data)
2. Success (201): auto-calls `triggerPipeline(curriculum_id)` → navigates to pipeline status page
3. Error (400): renders per-row error table (row number, field, message); row=0 shown as "—" (file-level error)

### Pipeline poller
- TanStack Query `refetchInterval` returns `false` when `status === "done" | "failed"`, halting polls automatically
- `staleTime: 0` ensures every poll returns fresh data from the API
- Progress bar transitions with CSS `transition-all duration-500` for smooth animation
- Color: blue (running) → green (done) → red accent (failed with failures > 0)

### Invite link
- Derived from `profile.enrolment_code` via `${window.location.origin}/enrol/${code}`
- Copy-to-clipboard uses `navigator.clipboard.writeText`; 2 s feedback state
- Displayed on both `/school/students` (as invite link) and `/school/settings` (as raw code)

### Role gating
- `TeachersPage` renders an access-denied message for non-admin teachers (no redirect — avoids SSR issues)
- `SchoolNav` filters `Teachers` item: `!item.adminOnly || teacher?.role === "school_admin"`
- Billing portal button on Settings page is rendered only for `school_admin`

### Email roster parsing
- Client-side: `raw.split(/[\n,;]+/).map(trim).filter(includes('@'))`
- Supports newline, comma, and semicolon delimiters
- Count displayed live below the textarea

---

## Exit Criteria Met
- ✅ XLSX upload form with per-row error table
- ✅ Pipeline poller (5 s interval, auto-stops on done/failed)
- ✅ Student roster with invite link + bulk email enrol
- ✅ Teacher invite (school_admin only)
- ✅ School settings + billing portal
- ✅ 76 tests passing
- ✅ Typecheck clean
- ✅ 43-route production build

---

## Phase W6 Preview

Next phase: **Admin Console** — internal team login (local bcrypt), RBAC-filtered sidebar, platform analytics, content pipeline management, content review queue, user management, audit log.

Routes: `/admin/login`, `/admin/dashboard`, `/admin/analytics`, `/admin/pipeline`, `/admin/content-review`, `/admin/users`, `/admin/schools`, `/admin/audit`, and more.
