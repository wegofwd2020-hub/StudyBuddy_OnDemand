# Phase W4 — School Portal (Teacher Reporting) — PRE

**Date:** 2026-03-27
**Preceding phase:** W3 — Student Account & Subscription (complete)
**Goal:** Build the full school portal (teacher + school_admin) covering all 13 page targets and 6 report types.

---

## Scope

### Pages to build

| # | Route | Description | Backend endpoint |
|---|---|---|---|
| T-01 | `/school/dashboard` | KPI cards, alert badge, quick links | `GET /reports/school/{id}/overview` |
| T-02 | `/school/class/[class_id]` | Student completion table (filterable by grade/subject) | `GET /analytics/school/{id}/class` |
| T-03 | `/school/student/[student_id]` | Per-student timeline, quiz scores, session history | `GET /reports/school/{id}/student/{student_id}` |
| T-04 | `/school/reports/overview` | Summary table + KPI cards with period selector | `GET /reports/school/{id}/overview?period=` |
| T-05 | `/school/reports/trends` | Line chart: lesson views + scores week-over-week | `GET /reports/school/{id}/trends?period=` |
| T-06 | `/school/reports/at-risk` | Curriculum-health struggling-tier table, drill-down links | `GET /reports/school/{id}/curriculum-health` |
| T-07 | `/school/reports/units` | Per-unit pass rate bar chart + data table | `GET /reports/school/{id}/unit/{unit_id}` (list via curriculum-health) |
| T-08 | `/school/reports/engagement` | Active %, streak leaders, dropout-risk list | Derived from `overview` + `curriculum-health` |
| T-09 | `/school/reports/feedback` | Unreviewed feedback cards by unit, mark-reviewed | `GET /reports/school/{id}/feedback` |
| T-10 | `/school/reports/export` | Report-type + date selector → CSV download via papaparse | `POST /reports/school/{id}/export` |
| T-16 | `/school/alerts` | Alert inbox, dismiss / acknowledge | `GET /reports/school/{id}/alerts` |
| T-17 | `/school/digest` | Digest subscription settings management | `POST /reports/school/{id}/digest/subscribe` |

### Components to build

| Component | Purpose |
|---|---|
| `components/layout/SchoolNav.tsx` | Sidebar navigation for all school portal pages |

### API layer

| Module | Exports |
|---|---|
| `lib/api/school-client.ts` | Axios instance using `sb_teacher_token`; 401 → `/school/login` |
| `lib/api/reports.ts` | All 6 report types + alerts + export + digest |

### Hooks

| Hook | Purpose |
|---|---|
| `lib/hooks/useTeacher.ts` | Decode teacher JWT from `sb_teacher_token`; expose `school_id`, `teacher_id`, `role` |

### Tests

| File | Coverage |
|---|---|
| `tests/unit/csv-export.test.ts` | CSV row building, header correctness, encoding |
| `tests/unit/alert-dismiss.test.ts` | Alert dismiss mutation; optimistic update; error rollback |

---

## Key Design Decisions

### Separate axios client for school portal
Teachers use a separate JWT (`sb_teacher_token`) from students (`sb_token`). A dedicated `schoolApi` client reads from `sb_teacher_token` so teacher-authenticated requests don't accidentally use the student token, and 401s redirect to `/school/login` (not `/login`).

### School ID resolution
All report endpoints require `school_id` in the URL path. The `useTeacher` hook decodes it from the `sb_teacher_token` JWT payload (claim `school_id`). This avoids an extra API call and is consistent with how the backend embeds `school_id` in the JWT.

### Auth guard
`app/(school)/layout.tsx` checks the Auth0 session (server-side) and redirects to `/school/login` if missing. The teacher JWT exchange is handled client-side in the school login page (Phase W1 built the page shell; teacher exchange is wired here).

### Report charts
- Trends (T-05): Recharts `LineChart` with two series (`lessons_viewed`, `avg_score_pct`)
- Unit Performance (T-07): Recharts `BarChart` with `first_attempt_pass_rate_pct` per unit
- Colors: blue for lesson activity, green for pass rate (consistent with student portal)

### CSV export strategy
Use papaparse `unparse()` client-side for instant preview exports. For server-generated exports (full dataset), call `POST /reports/school/{id}/export` and poll the returned `download_url`.

### Feedback mark-reviewed
No dedicated `PATCH /reports/feedback/{id}/reviewed` endpoint exists in the backend Phase 11 implementation. The feedback report is read-only from the teacher portal; marking reviewed is handled in the admin console (Phase W6). The feedback page shows unreviewed items but does not send a mutation.

---

## Dependencies

- `papaparse` — CSV generation (already in `package.json` if not, will add)
- `recharts` — already installed from Phase W2
- `@tanstack/react-query` — already installed

---

## Exit Criteria

- All 12 routes render correctly (no type errors, no runtime crashes on mock data)
- Trends line chart displays with correct axes
- Unit performance bar chart renders
- CSV export downloads a valid CSV from the client-side papaparse path
- Alert dismiss removes the item from the list (optimistic update)
- `npm run typecheck` passes
- `npm run build` succeeds with all 38 expected routes
- Unit tests pass (target: ≥ 38 total)
