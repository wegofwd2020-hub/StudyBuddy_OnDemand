/**
 * Test data for section 2.11 — Paywall Page (`/paywall`)
 * Covers TC-IDs: STU-34, STU-35
 *
 * This page is a static client component — no API calls needed.
 * Unit tests render PaywallPage directly with mocked next-intl.
 *
 * STU-34: Paywall explains that the school controls access.
 * STU-35: The only CTA returns to the dashboard.
 *
 * Students cannot buy a subscription — individual student billing was removed
 * in migration 0027 (ADR-001). The page used to advertise "$9.99/month" and a
 * Subscribe button that led to endpoints returning 404 (#604), so the prices
 * and the CTA are gone rather than restated here.
 */

// ---------------------------------------------------------------------------
// Expected UI strings
// (keys match useTranslations("subscription_screen") — mock returns key as-is)
// ---------------------------------------------------------------------------

export const PAYWALL_STRINGS = {
  title: "school_managed_title",
  paywallMsg: "paywall_msg_school",
  help: "school_managed_help",
  backToDashboard: "back_to_dashboard",
} as const;

// ---------------------------------------------------------------------------
// Expected hrefs (STU-35)
// ---------------------------------------------------------------------------

export const PAYWALL_HREFS = {
  dashboardHref: "/dashboard",
} as const;
