# Phase W3 — Student Account & Subscription — POST

**Completed:** 2026-03-27
**Tests:** 31 passing (added 11 new — 7 subscription unit tests + 4 carried from W2)
**Build:** Clean (26 routes, 0 errors, 0 type errors)

---

## Deliverables

### Pages added

| Route                           | Page                                                                    | Req        |
| ------------------------------- | ----------------------------------------------------------------------- | ---------- |
| `/account/subscription`         | Plan selector (monthly/annual toggle), current plan status, cancel flow | S-10, S-11 |
| `/account/subscription/success` | Post-Stripe-checkout confirmation; invalidates subscription cache       | —          |
| `/account/settings`             | Display name, locale (EN/FR/ES), notification toggles                   | S-12       |
| `/enrol/[token]`                | School enrolment confirmation (calls `POST /school/enrol/confirm`)      | S-15       |

### Components added

| Component                            | Purpose                                            |
| ------------------------------------ | -------------------------------------------------- |
| `components/student/TrialBanner.tsx` | Sticky top banner; blue → red when ≤ 3 days remain |

### API layer added

| Module                    | Exports                                                                                |
| ------------------------- | -------------------------------------------------------------------------------------- |
| `lib/api/subscription.ts` | `getSubscriptionStatus`, `createCheckout`, `getBillingPortalUrl`, `cancelSubscription` |
| `lib/api/settings.ts`     | `getAccountSettings`, `saveAccountSettings`                                            |
| `lib/api/school.ts`       | `confirmEnrolment`                                                                     |

### Hooks added

| Hook                           | Purpose                                                                 |
| ------------------------------ | ----------------------------------------------------------------------- |
| `lib/hooks/useSubscription.ts` | `useSubscription()` (TanStack Query), `trialDaysRemaining(iso)` utility |

### Tests added

| File                              | Tests | Coverage                                                    |
| --------------------------------- | ----- | ----------------------------------------------------------- |
| `tests/unit/subscription.test.ts` | 11    | `trialDaysRemaining` edge cases; all 4 API functions mocked |

---

## Subscription Page State Machine

The subscription page handles all 5 plan states cleanly:

| `status`                           | Plan selector shown | Cancel link shown | Manage billing shown |
| ---------------------------------- | ------------------- | ----------------- | -------------------- |
| `free`                             | ✅                  | —                 | —                    |
| `trial`                            | ✅                  | —                 | —                    |
| `active`                           | —                   | ✅                | ✅                   |
| `cancelled` (cancel_at_period_end) | ✅                  | —                 | ✅                   |
| `past_due`                         | —                   | —                 | ✅                   |

Cancel flow: link → confirmation card → `POST /subscription/cancel` → cache invalidation → success message.

---

## Layout Update

`app/(student)/layout.tsx` now wraps all student pages in:

1. `QueryProvider` — TanStack Query context
2. `TrialBanner` — shown only when `status === "trial"`
3. `OfflineBanner` — shown when offline (from Phase W2)

---

## Key Decisions

- **Locale switcher** is a segmented button group (not a dropdown) — 3 options fits the width cleanly.
- **Notification checkboxes** use custom styled divs instead of `<input type="checkbox">` to match Tailwind aesthetics; underlying `<input>` is sr-only for accessibility.
- **Enrolment page** reads the `token` from `useParams` and calls the API on mount; error message is taken from the API response detail field when available.
- **Success page** invalidates `["subscription"]` query on mount so the trial banner disappears immediately without a page reload.

---

## Phase W4 Preview

Next phase: **School Portal** — teacher login, class roster, curriculum assignment, student progress view, bulk enrolment invite flow.

Routes to build: `/school/dashboard`, `/school/classes`, `/school/classes/[id]`, `/school/students/[id]`, `/school/curriculum`, `/school/invite`.
