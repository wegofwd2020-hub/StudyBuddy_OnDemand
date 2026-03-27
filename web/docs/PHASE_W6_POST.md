# Phase W6 — Admin Console — POST

**Completed:** 2026-03-27
**Tests:** 99 passing (added 23 new — 11 RBAC + 8 review actions + 5 health poller / colour / interval)
**Build:** Clean (56 routes, 0 type errors)

---

## Deliverables

### Routes added

| Route | Page | Req |
|---|---|---|
| `/admin/login` | Local bcrypt login; stores `sb_admin_token`; redirects to dashboard on success | W6-1 |
| `/admin/dashboard` | Subscription KPI cards (total active, MRR, new/cancelled, churn) + pipeline summary | W6-2 |
| `/admin/analytics` | Subscription breakdown table + struggle report (unit, grade, avg score, fail rate) | W6-3 |
| `/admin/pipeline` | Jobs list (status badge, progress, triggered timestamp); auto-refreshes every 15 s | W6-4 |
| `/admin/pipeline/trigger` | Grade select, lang input, force checkbox; `product_admin`+ only | W6-5 |
| `/admin/pipeline/[job_id]` | Live progress bar + built/failed/total counts; reuses `getPipelineStatus` | W6-6 |
| `/admin/content-review` | Review queue with status filter tabs (pending/approved/published/rejected/blocked/all) | W6-7 |
| `/admin/content-review/[version_id]` | Lesson preview, quiz count, AlexJS score, annotations; role-gated action buttons | W6-8 |
| `/admin/feedback` | Student feedback with open/resolved filter, star rating, resolve action; `product_admin`+ | W6-9 |
| `/admin/health` | DB + Redis status banners; overall health banner; polls every 10 s | W6-10 |
| `/admin/audit` | Audit log table with action filter and pagination; `product_admin`+ | W6-11 |

### API modules added

| Module | Exports |
|---|---|
| `lib/api/admin-client.ts` | Axios client with `sb_admin_token`; 401 → `/admin/login` |
| `lib/api/admin.ts` | `adminLogin`, `getSubscriptionAnalytics`, `getStruggleReport`, `getPipelineJobs`, `triggerAdminPipeline`, `getReviewQueue`, `getReviewItem`, `approveReview`, `rejectReview`, `publishReview`, `rollbackReview`, `blockReview`, `getFeedbackList`, `resolveFeedback`, `getSystemHealth`, `getAuditLog` |

### Hooks added

| Hook | Exports |
|---|---|
| `lib/hooks/useAdmin.ts` | `useAdmin()` → `{ admin_id, role }`, `hasPermission(role, minRole)`, `AdminRole` type |

### Components added

| Component | Description |
|---|---|
| `components/layout/AdminNav.tsx` | Dark sidebar (gray-900); RBAC-filtered nav; role badge in footer; sign-out |

### Tests added

| File | Tests | Coverage |
|---|---|---|
| `tests/unit/admin-rbac.test.ts` | 11 | `hasPermission` for all 4 roles; sidebar filter logic for developer/tester/product_admin/super_admin |
| `tests/unit/review-actions.test.ts` | 8 | `approveReview`, `rejectReview`, `publishReview`, `rollbackReview`, `blockReview` API mocks; `getReviewQueue` with/without filter |
| `tests/unit/health-poller.test.ts` | 5 | `getSystemHealth` ok + error path; colour mapping; poll-always interval |

---

## Key Implementation Details

### Admin auth (no Auth0)
- `POST /admin/auth/login` → `{ token, admin_id }` stored as `sb_admin_token` in localStorage
- Admin layout is a **Client Component** (`"use client"`) — reads `sb_admin_token` on mount, redirects to `/admin/login` if absent
- Login page lives at `app/(public)/admin/login/` (outside the authenticated `(admin)` layout)
- `useAdmin()` hook decodes the JWT payload with `atob()` (same pattern as `useTeacher`)

### RBAC role rank
```ts
const ROLE_RANK = { developer: 0, tester: 1, product_admin: 2, super_admin: 3 };
hasPermission(role, minRole) // true when ROLE_RANK[role] >= ROLE_RANK[minRole]
```
- `Feedback`, `Audit Log` nav items: `minRole: "product_admin"`
- Pipeline trigger page: renders access-denied for `developer`/`tester` (no redirect)
- Content review actions: `publishReview`/`rollbackReview`/`blockReview` buttons conditionally rendered

### Content review action modal
- `reject` and `block` open an inline modal requiring a non-empty reason string
- `approve`, `publish`, `rollback` execute immediately without a modal
- All actions invalidate `["admin", "content-review"]` TanStack Query cache, then navigate back to queue

### Health page poll
- `refetchInterval: 10_000` — always polls (no stop condition; health must always refresh)
- Uses the unauthenticated base `api` client (`lib/api/client.ts`) since `GET /health` requires no auth

### Pipeline reuse
- `/admin/pipeline/[job_id]` calls `getPipelineStatus` from `lib/api/curriculum-admin.ts` (same endpoint as school portal)
- `/admin/pipeline/trigger` calls `triggerAdminPipeline` from `lib/api/admin.ts` (different endpoint: `POST /admin/pipeline/trigger`)

---

## Exit Criteria Met
- ✅ `/admin/login` authenticates via local bcrypt and stores `sb_admin_token`
- ✅ Admin layout redirects to login when token absent
- ✅ Subscription KPIs visible on dashboard
- ✅ Pipeline jobs list with trigger form (role-gated)
- ✅ Content review queue with approve/reject/publish/rollback/block
- ✅ System health page polling every 10 s
- ✅ RBAC sidebar filtering for all 4 roles
- ✅ 99 tests passing
- ✅ Typecheck clean
- ✅ 56-route production build

---

## Phase W7 Preview

Next phase: **Student Mobile App Polish** or **End-to-End Integration Tests** — TBD.

Candidates:
- Playwright E2E tests for the critical student flow (login → subject → lesson → quiz)
- School portal E2E tests (teacher login → curriculum upload → pipeline wait → student enrol)
- Admin console E2E tests (login → content review → publish)
