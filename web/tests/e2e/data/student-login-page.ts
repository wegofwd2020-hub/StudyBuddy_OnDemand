/**
 * Test data for section 1.3 — Student Login Page (`/login`)
 * Covers TC-IDs: PUB-17, PUB-18 (+ supporting elements)
 *
 * String values sourced from i18n/en.json and page.tsx hardcoded strings.
 */

// ---------------------------------------------------------------------------
// Page identity
// ---------------------------------------------------------------------------

export const PAGE = {
  url: "/login",
  title: "Welcome back",
  subtitle: "Sign in to continue learning",
} as const;

// ---------------------------------------------------------------------------
// PUB-17 — Auth0 sign-in button
// Auth0 initialises but returns null session in test env (no real cookie).
// We verify the link exists and points to the correct href; do NOT click it
// as it would trigger a full Auth0 redirect outside the app.
// ---------------------------------------------------------------------------

export const SIGN_IN_LINK = {
  text: "Sign in with school account",
  /** Handled by Auth0 middleware — navigates to Auth0 login */
  href: "/auth/login",
} as const;

// ---------------------------------------------------------------------------
// PUB-18 — Sign up free link
// ---------------------------------------------------------------------------

export const SIGN_UP_LINK = {
  text: "Sign up free",
  href: "/signup",
} as const;

// ---------------------------------------------------------------------------
// Supporting links on the page (additional coverage)
// ---------------------------------------------------------------------------

export const SUPPORTING_LINKS: ReadonlyArray<{ text: string; href: string }> = [
  { text: "Forgot password?",  href: "/reset-password" },
  { text: "School sign in",    href: "/school/login"   },
];
