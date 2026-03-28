/**
 * Test data for section 2.11 — Paywall Page (`/paywall`)
 * Covers TC-IDs: STU-34, STU-35
 *
 * This page is a static client component — no API calls needed.
 * Unit tests render PaywallPage directly with mocked next-intl.
 *
 * STU-34: Paywall page renders — upgrade prompt with subscription link visible.
 * STU-35: Upgrade button href points to /account/subscription.
 */

// ---------------------------------------------------------------------------
// Expected UI strings
// (keys match useTranslations("subscription_screen") — mock returns key as-is)
// ---------------------------------------------------------------------------

export const PAYWALL_STRINGS = {
  title:           "title",
  paywallMsg:      "paywall_msg",
  subscribeBtn:    "subscribe_btn",
  annualSavings:   "annual_savings",
  backToDashboard: "Back to Dashboard",
  monthlyPrice:    "$9.99/month",
  annualPrice:     "$99.99/year",
} as const;

// ---------------------------------------------------------------------------
// Expected hrefs (STU-35)
// ---------------------------------------------------------------------------

export const PAYWALL_HREFS = {
  upgradeHref:   "/account/subscription",
  dashboardHref: "/dashboard",
} as const;
