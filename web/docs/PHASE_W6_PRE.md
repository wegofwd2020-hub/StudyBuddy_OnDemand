# Phase W6 — Admin Console — PRE

**Started:** 2026-03-27
**Branch:** main
**Preceding build:** 76 tests passing, 43 routes, 0 type errors (Phase W5)

---

## Scope

Build the internal Admin Console for the StudyBuddy platform team.
Admins authenticate via local bcrypt (no Auth0). The backend issues a separate
`sb_admin_token` signed with `ADMIN_JWT_SECRET`.

RBAC roles from `backend/src/core/permissions.py`:

| Role | Key permissions |
|---|---|
| `developer` | `content:read`, `review:read`, `review:rate` |
| `tester` | `developer` + `review:annotate` |
| `product_admin` | `tester` + `publish`, `rollback`, `block`, `regenerate`, `school:manage`, `feedback:view` |
| `super_admin` | wildcard `"*"` — all permissions |

---

## Routes to Add (10 new pages)

| Route | Page | Auth |
|---|---|---|
| `/admin/login` | Local bcrypt login (public) | None |
| `/admin/dashboard` | Subscription KPIs + pipeline summary | Any admin |
| `/admin/analytics` | Subscription funnel + struggle report | Any admin |
| `/admin/pipeline` | Pipeline jobs list | Any admin |
| `/admin/pipeline/trigger` | Trigger new pipeline job | `product_admin`, `super_admin` |
| `/admin/pipeline/[job_id]` | Pipeline job detail + progress poller | Any admin |
| `/admin/content-review` | Review queue list | Any admin |
| `/admin/content-review/[version_id]` | Review detail + action buttons | Role-filtered actions |
| `/admin/feedback` | Feedback queue | `product_admin`, `super_admin` |
| `/admin/health` | System health (DB + Redis status, 10 s poll) | Any admin |

---

## API Modules to Add

| Module | Exports |
|---|---|
| `lib/api/admin-client.ts` | Axios client with `sb_admin_token`; 401 → `/admin/login` |
| `lib/api/admin.ts` | `adminLogin`, `getSubscriptionAnalytics`, `getStruggleReport`, `getPipelineJobs`, `triggerAdminPipeline`, `getReviewQueue`, `getReviewItem`, `approveReview`, `rejectReview`, `publishReview`, `rollbackReview`, `blockReview`, `getFeedbackList`, `getSystemHealth`, `getAuditLog` |

---

## Hooks to Add

| Hook | Purpose |
|---|---|
| `lib/hooks/useAdmin.ts` | Decode `sb_admin_token`; expose `{ admin_id, role }` |

---

## Components to Add

| Component | Purpose |
|---|---|
| `components/layout/AdminNav.tsx` | Collapsible sidebar; RBAC-filtered nav items; `super_admin` badge |

---

## Tests to Add (target: +22 tests → 98 total)

| File | Tests | Coverage |
|---|---|---|
| `tests/unit/admin-rbac.test.ts` | 9 | RBAC sidebar item filtering for all 4 roles; `useAdmin` JWT decode; null token |
| `tests/unit/review-actions.test.ts` | 8 | `approveReview`, `rejectReview`, `publishReview`, `rollbackReview`, `blockReview` API mocks |
| `tests/unit/health-poller.test.ts` | 5 | `getSystemHealth` API mock; status-to-colour mapping; poll-stop (no auto-stop — health always polls) |

---

## Key Design Decisions

### Admin auth pattern (no Auth0)
- Login page at `app/(public)/admin/login/page.tsx` — outside the authenticated `(admin)` layout
- `POST /admin/auth/login` returns `{ token, admin_id }` → stored as `sb_admin_token` in localStorage
- Admin layout (`app/(admin)/layout.tsx`) is a **Client Component**: reads `sb_admin_token` on mount, redirects to `/admin/login` if missing
- Token decoded by `useAdmin` hook (same `atob()` pattern as `useTeacher`)

### RBAC in sidebar
- `AdminNav` reads `useAdmin().role`
- Nav items carry `minRole` or `allowedRoles` array; items are hidden for roles without permission
- No full-page redirect for insufficient role — renders access-denied inline (consistent with W5 teachers page)

### Pipeline reuse
- `/admin/pipeline/[job_id]` reuses `getPipelineStatus` from `lib/api/curriculum-admin.ts` (same backend endpoint)
- Admin trigger uses a different endpoint (`POST /admin/pipeline/trigger` with `{ grade, lang, force }`) vs school upload flow

### Health page
- `refetchInterval: 10_000` — always polls (no stop condition); shows last-checked timestamp
- Color: green (ok) / red (error) per service

---

## Exit Criteria

- [ ] `/admin/login` authenticates and stores `sb_admin_token`
- [ ] Admin layout redirects to login when token is absent
- [ ] Subscription KPIs visible on dashboard
- [ ] Pipeline jobs list with trigger form
- [ ] Content review queue with approve/reject/publish/rollback/block actions
- [ ] System health page polling every 10 s
- [ ] RBAC sidebar filtering works for all 4 roles
- [ ] 98 tests passing
- [ ] Typecheck clean
- [ ] Production build succeeds
