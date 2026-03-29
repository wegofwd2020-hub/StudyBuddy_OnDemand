/**
 * Test data for section 2.13 — Subscription Page (`/account/subscription`)
 * Covers TC-IDs: STU-42, STU-43, STU-44, STU-45
 *
 * Auth note: requires a real Auth0 session for E2E.
 * Unit tests mock useSubscription(), createCheckout(), getBillingPortalUrl().
 *
 * STU-43 (Stripe checkout): createCheckout() returns a URL which the page
 * assigns to window.location.href — tested by mocking window.location.
 * STU-44 (billing portal): getBillingPortalUrl() same pattern.
 *
 * Backend API routes for E2E page.route() interception:
 *   GET  /api/v1/subscription/status   → MOCK_SUB_FREE | MOCK_SUB_TRIAL | MOCK_SUB_ACTIVE
 *   POST /api/v1/subscription/checkout → { checkout_url: STRIPE_CHECKOUT_URL }
 *   POST /api/v1/subscription/portal   → { portal_url: STRIPE_PORTAL_URL }
 */

import type { SubscriptionState } from "@/lib/api/subscription";

// ---------------------------------------------------------------------------
// Mock subscription states (STU-42)
// ---------------------------------------------------------------------------

export const MOCK_SUB_FREE: SubscriptionState = {
  status: "free",
  plan: null,
  trial_ends_at: null,
  current_period_end: null,
  cancel_at_period_end: false,
};

export const MOCK_SUB_TRIAL: SubscriptionState = {
  status: "trial",
  plan: null,
  trial_ends_at: new Date(Date.now() + 5 * 24 * 60 * 60 * 1000).toISOString(), // 5 days from now
  current_period_end: null,
  cancel_at_period_end: false,
};

export const MOCK_SUB_ACTIVE_MONTHLY: SubscriptionState = {
  status: "active",
  plan: "student_monthly",
  trial_ends_at: null,
  current_period_end: "2026-04-28T00:00:00Z",
  cancel_at_period_end: false,
};

export const MOCK_SUB_ACTIVE_ANNUAL: SubscriptionState = {
  status: "active",
  plan: "student_annual",
  trial_ends_at: null,
  current_period_end: "2027-03-28T00:00:00Z",
  cancel_at_period_end: false,
};

export const MOCK_SUB_CANCELLED: SubscriptionState = {
  status: "active",
  plan: "student_monthly",
  trial_ends_at: null,
  current_period_end: "2026-04-28T00:00:00Z",
  cancel_at_period_end: true,
};

// ---------------------------------------------------------------------------
// Mock Stripe URLs (STU-43, STU-44)
// ---------------------------------------------------------------------------

export const STRIPE_CHECKOUT_URL = "https://checkout.stripe.com/pay/cs_test_abc123";
export const STRIPE_PORTAL_URL = "https://billing.stripe.com/session/bps_test_xyz789";

// ---------------------------------------------------------------------------
// Expected UI strings
// (keys match useTranslations("subscription_screen") — mock returns key as-is)
// ---------------------------------------------------------------------------

export const SUBSCRIPTION_STRINGS = {
  title: "title",
  currentPlanFree: "current_plan_free",
  subscribeBtn: "subscribe_btn",
  // Static strings
  currentPlanLabel: "Current plan",
  choosePlanHeading: "Choose a plan",
  studentPlan: "Student Plan",
  manageBilling: "Manage billing",
  freeTrial: "Free Trial",
  studentMonthly: "Student — Monthly",
  studentAnnual: "Student — Annual",
  monthlyPrice: "$9.99",
  annualPrice: "$99.99",
  annualSaving: "Save $19.89 vs monthly",
  trialSuffix: "days remaining in trial",
  cancelSubscription: "Cancel subscription",
  cancelConfirmMsg: "Cancel your subscription?",
} as const;

// ---------------------------------------------------------------------------
// Plan features list (STU-42)
// ---------------------------------------------------------------------------

export const PLAN_FEATURES = [
  "Unlimited lessons",
  "Audio narration",
  "All 3 languages",
  "Offline access",
  "Experiment guides",
  "Progress tracking",
] as const;
