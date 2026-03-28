/**
 * Test data for section 2.14 — Subscription Success (`/account/subscription/success`)
 * Covers TC-IDs: STU-46, STU-47
 *
 * This page is a static client component — no API calls needed.
 * Unit tests render SubscriptionSuccessPage directly.
 *
 * STU-46: Success icon + confirmation message shown.
 * STU-47: "Go to dashboard" link visible.
 */

// ---------------------------------------------------------------------------
// Expected UI strings
// ---------------------------------------------------------------------------

export const SUCCESS_STRINGS = {
  heading:        "You're subscribed!",
  bodyText:       "Welcome to StudyBuddy OnDemand. You now have full access to all lessons, quizzes, and offline content.",
  dashboardBtn:   "Go to dashboard",
  subjectsBtn:    "Browse subjects",
} as const;

// ---------------------------------------------------------------------------
// Expected hrefs (STU-47)
// ---------------------------------------------------------------------------

export const SUCCESS_HREFS = {
  dashboard: "/dashboard",
  subjects:  "/subjects",
} as const;
