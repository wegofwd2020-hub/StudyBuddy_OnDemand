/**
 * Test data for section 1.4 — School Login Page (`/school/login`)
 * Covers TC-IDs: PUB-19, PUB-20, PUB-21
 *
 * String values sourced from i18n/en.json and page.tsx hardcoded strings.
 */

// ---------------------------------------------------------------------------
// Page identity
// ---------------------------------------------------------------------------

export const PAGE = {
  url: "/school/login",
  title: "Teacher & School sign in",
  subtitle: "Access your class dashboard",
} as const;

// ---------------------------------------------------------------------------
// PUB-19 — Auth0 sign-in button (school connection)
// AnchorButton renders as <a> — verify href only; do NOT click (Auth0 redirect)
// ---------------------------------------------------------------------------

export const SIGN_IN_LINK = {
  text: "Sign in with school account",
  /** Auth0 with school connection param */
  href: "/auth/login?connection=school",
} as const;

// ---------------------------------------------------------------------------
// PUB-20 — Student login link
// ---------------------------------------------------------------------------

export const STUDENT_LOGIN_LINK = {
  text: "Student login",
  href: "/login",
} as const;

// ---------------------------------------------------------------------------
// PUB-21 — Contact us link
// ---------------------------------------------------------------------------

export const CONTACT_LINK = {
  text: "Contact us",
  href: "/contact",
} as const;
