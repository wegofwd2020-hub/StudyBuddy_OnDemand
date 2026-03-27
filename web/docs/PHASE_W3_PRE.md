# Phase W3 — Student Portal: Account & Subscription
## Pre-Implementation Document

Date: 2026-03-27
Status: Planning

---

## Scope

Complete the student portal by adding subscription management, account settings,
enrolment confirmation, a trial countdown banner, and a post-payment success page.
After W3, every student-facing page in the plan is built.

---

## Pages

| ID | Route | Description |
|---|---|---|
| S-10 | `/account/subscription` | Plan cards, Stripe checkout redirect, trial status |
| S-11 | `/account/subscription` | Same page — manage/cancel section when already subscribed |
| S-12 | `/account/settings` | Locale switcher, notification toggles, display name |
| S-15 | `/enrol/[token]` | Student accepts school enrolment invite link |
| — | `/account/subscription/success` | Post-Stripe redirect confirmation, redirect to dashboard |

---

## New Files

```
web/
  app/(student)/
    account/
      settings/page.tsx             ← S-12
      subscription/
        page.tsx                    ← S-10 / S-11
        success/page.tsx            ← post-payment success
    enrol/[token]/page.tsx          ← S-15

  components/
    student/
      TrialBanner.tsx               ← "X days left in trial" banner shown across portal

  lib/
    api/
      subscription.ts               ← getSubscriptionStatus(), createCheckout(),
                                       getBillingPortalUrl(), cancelSubscription()
      school.ts                     ← confirmEnrolment()
      settings.ts                   ← getAccountSettings(), saveAccountSettings()
    hooks/
      useSubscription.ts            ← TanStack Query wrapper for subscription status

  tests/unit/
    subscription.test.ts            ← plan state logic, trial-days calculation
```

---

## API Endpoints Used

| Endpoint | Used by |
|---|---|
| `GET /subscription/status` | S-10, S-11, TrialBanner |
| `POST /subscription/checkout` | S-10 (new subscription) |
| `GET /subscription/billing-portal` | S-11 (manage existing subscription) |
| `POST /subscription/cancel` | S-11 (cancel flow) |
| `POST /school/enrol/confirm` | S-15 |
| `GET /auth/settings` | S-12 |
| `PATCH /auth/settings` | S-12 |

---

## Key Design Decisions

### Subscription page (S-10 / S-11 combined)
The subscription page serves double duty:
- **No active subscription** → show plan cards + "Subscribe" button
- **Trial** → show trial countdown + upgrade CTA
- **Active** → show current plan badge + "Manage billing" (Stripe portal) + cancel option
- **Cancelled** → show resubscribe CTA

Stripe checkout is server-initiated: `POST /subscription/checkout` returns a
`checkout_url`; the browser is redirected there. The success URL is
`/account/subscription/success?session_id={CHECKOUT_SESSION_ID}`.

### Locale switcher
Locale is stored in a `locale` cookie (already read by `lib/i18n/request.ts`).
Changing locale sets the cookie via a server action then does a full page reload.
This ensures next-intl picks up the new locale on the next render — no client-side
string swapping.

### Trial countdown banner (TrialBanner)
Conditionally rendered in the student layout above the main content area.
Reads subscription status from TanStack Query cache (shared with the subscription
page). Shows: "X days left in your free trial. Upgrade now →"

### Enrolment confirm (S-15)
Public-accessible token URL with auth guard. Flow:
1. Student visits `/enrol/[token]` (linked from email)
2. Auth guard ensures they're logged in (redirect to login with return URL if not)
3. `POST /school/enrol/confirm` with the token
4. On success → show confirmation + redirect to `/dashboard`
5. On error (token expired/invalid) → show clear error with support link

---

## Exit Criteria

- [ ] Subscription page renders all plan states (free / trial / active / cancelled)
- [ ] Clicking Subscribe redirects to Stripe checkout URL
- [ ] Manage billing redirects to Stripe billing portal
- [ ] Cancel shows confirmation dialog before calling `POST /subscription/cancel`
- [ ] Account settings saves locale + notifications; locale change reloads with new strings
- [ ] Trial banner appears when status is "trial"; hidden when active/free
- [ ] Enrolment confirm page handles success and error states
- [ ] Post-payment success page confirms and auto-redirects to dashboard
- [ ] Unit tests: subscription state logic, trial-days calculation
- [ ] TypeScript: 0 errors
- [ ] Build: 0 errors
