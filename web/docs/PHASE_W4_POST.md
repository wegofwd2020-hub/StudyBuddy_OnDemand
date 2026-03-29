# Phase W4 — School Portal (Teacher Reporting) — POST

**Completed:** 2026-03-27
**Tests:** 45 passing (added 14 new — 7 CSV + 7 alert dismiss)
**Build:** Clean (38 routes, 0 type errors)

---

## Deliverables

### Routes added (all under `/school/*`)

| Route                          | Page                                                          | Req  |
| ------------------------------ | ------------------------------------------------------------- | ---- |
| `/school/dashboard`            | KPI cards, alerts badge, quick links                          | T-01 |
| `/school/class/[class_id]`     | Sortable student completion table, grade filter               | T-02 |
| `/school/student/[student_id]` | Per-student stats + per-unit progress table                   | T-03 |
| `/school/reports/overview`     | 6 KPI cards + period selector + struggle/no-activity lists    | T-04 |
| `/school/reports/trends`       | Two Recharts line charts + weekly data table                  | T-05 |
| `/school/reports/at-risk`      | Health tier summary + struggling/watch unit tables            | T-06 |
| `/school/reports/units`        | Horizontal bar chart (color-coded by tier) + full table       | T-07 |
| `/school/reports/engagement`   | Active %, audio rate, inactive students, zero-activity units  | T-08 |
| `/school/reports/feedback`     | Per-unit feedback cards with star ratings + category badges   | T-09 |
| `/school/reports/export`       | 3-report CSV export via papaparse (BOM-prefixed for Excel)    | T-10 |
| `/school/alerts`               | Alert inbox with optimistic dismiss + acknowledged section    | T-16 |
| `/school/digest`               | Digest subscription settings (email, timezone, enable toggle) | T-17 |

### Components added

| Component                         | Purpose                                            |
| --------------------------------- | -------------------------------------------------- |
| `components/layout/SchoolNav.tsx` | Sidebar with alert badge counter + reports sub-nav |

### API layer added

| Module                     | Exports                                                                      |
| -------------------------- | ---------------------------------------------------------------------------- |
| `lib/api/school-client.ts` | Axios instance for teacher JWT (`sb_teacher_token`); 401→`/school/login`     |
| `lib/api/reports.ts`       | All 6 report types, alerts, alert settings, export trigger, digest subscribe |

### Hooks added

| Hook                      | Purpose                                                      |
| ------------------------- | ------------------------------------------------------------ |
| `lib/hooks/useTeacher.ts` | Decode teacher JWT; expose `school_id`, `teacher_id`, `role` |

### Tests added

| File                               | Tests | Coverage                                                                   |
| ---------------------------------- | ----- | -------------------------------------------------------------------------- |
| `tests/unit/csv-export.test.ts`    | 7     | papaparse unparse: headers, BOM, comma escaping, empty rows, null handling |
| `tests/unit/alert-dismiss.test.ts` | 7     | `getAlerts` API, optimistic dismiss logic, `updateAlertSettings` payload   |

---

## Route Conflict Resolution

Initial implementation placed pages at `app/(school)/dashboard/`, `app/(school)/alerts/`, etc. This caused a build error because route groups are transparent — `/dashboard` would conflict with `app/(student)/dashboard/`.

**Fix:** All school portal pages live under `app/(school)/school/` which resolves to `/school/*` URLs. The layout at `app/(school)/layout.tsx` correctly wraps all these routes.

---

## Data Strategy

| Report                     | API endpoint                                    |
| -------------------------- | ----------------------------------------------- |
| Dashboard, Overview        | `GET /reports/school/{id}/overview`             |
| Trends                     | `GET /reports/school/{id}/trends`               |
| At-Risk, Units, Engagement | `GET /reports/school/{id}/curriculum-health`    |
| Student Detail             | `GET /reports/school/{id}/student/{student_id}` |
| Class Overview             | `GET /analytics/school/{id}/class`              |
| Feedback                   | `GET /reports/school/{id}/feedback`             |
| Alerts                     | `GET /reports/school/{id}/alerts`               |

Engagement report derives from two cached queries (`overview` 30d + `curriculum-health`) to avoid a dedicated endpoint.

---

## Key Decisions

- **Separate axios client** (`school-client.ts`): reads `sb_teacher_token` not `sb_token`; 401 redirects to `/school/login` (not `/login`).
- **Alert dismiss is optimistic**: local `Set<string>` + `qc.setQueryData` update; no API call needed (no dismiss endpoint in Phase 11 backend).
- **CSV export is client-side only** for the 3 common reports; uses BOM prefix (`\uFEFF`) for Excel UTF-8 compatibility.
- **`useTeacher` hook** decodes JWT in browser without an extra API call — school_id is embedded in the JWT payload.
- **TanStack Query** sharing: `curriculum-health` query is shared between At-Risk, Units, and Engagement pages — one network call, three consumers.

---

## Phase W5 Preview

Next phase: **School Portal Admin & Curriculum** — XLSX upload, pipeline status poller, student roster management, teacher invites, school settings.

Routes: `/school/curriculum`, `/school/curriculum/pipeline/[job_id]`, `/school/students`, `/school/teachers`, `/school/settings`.
