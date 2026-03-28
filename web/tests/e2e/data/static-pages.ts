/**
 * Test data for section 1.5 — Static Pages
 * Covers TC-IDs: PUB-22 through PUB-28
 *
 * String values sourced from i18n/en.json and page.tsx hardcoded strings.
 */

// ---------------------------------------------------------------------------
// PUB-22 — Terms of Service (`/terms`)
// ---------------------------------------------------------------------------

export const TERMS = {
  url: "/terms",
  heading: "Terms of Service",
  sectionHeadings: [
    "1. Acceptance of Terms",
    "2. Subscription and Payments",
    "3. Acceptable Use",
    "4. Content",
    "5. Children's Privacy",
    "6. Limitation of Liability",
    "7. Contact",
  ],
  contactEmail: "legal@studybuddy.com",
} as const;

// ---------------------------------------------------------------------------
// PUB-23 — Privacy Policy (`/privacy`)
// ---------------------------------------------------------------------------

export const PRIVACY = {
  url: "/privacy",
  heading: "Privacy Policy",
  sectionHeadings: [
    "Data We Collect",
    "COPPA (Children Under 13)",
    "GDPR (EU Users)",
    "FERPA (School Users)",
    "Data Retention",
    "Third-Party Services",
  ],
} as const;

// ---------------------------------------------------------------------------
// PUB-24 — Contact Page (`/contact`)
// ---------------------------------------------------------------------------

export const CONTACT = {
  url: "/contact",
  heading: "Get in touch",
  /** Input field ids from the form */
  fields: [
    { id: "name",    label: "Name",    type: "text"  },
    { id: "email",   label: "Email",   type: "email" },
    { id: "subject", label: "Subject", type: "text"  },
    { id: "message", label: "Message", type: "textarea" },
  ],
  submitButton: "Send message",
  successText: "Message sent!",
  /** Valid form payload for submission test */
  validPayload: {
    name:    "Test User",
    email:   "test@example.com",
    subject: "Test enquiry",
    message: "This is a test message from the E2E harness.",
  },
} as const;

// ---------------------------------------------------------------------------
// PUB-25 — Signup Page (`/signup`)
// ---------------------------------------------------------------------------

export const SIGNUP = {
  url: "/signup",
  title: "Create your account",
  subtitle: "Start your free trial today",
  ctaText: "Create free account",
  /** AnchorButton href — Auth0 signup screen_hint; do NOT click */
  ctaHref: "/auth/login?screen_hint=signup",
  perks: [
    "5 free lessons every month",
    "Audio narration for every lesson",
    "No credit card required",
  ],
  signInLink: { text: "Sign in", href: "/login" },
} as const;

// ---------------------------------------------------------------------------
// PUB-26 — 404 Page
// ---------------------------------------------------------------------------

export const NOT_FOUND = {
  url: "/this-page-does-not-exist",
  expectedStatus: 404,
  headingText: "Page not found",
} as const;

// ---------------------------------------------------------------------------
// PUB-27 — COPPA Consent Page (`/consent`)
// ---------------------------------------------------------------------------

export const CONSENT = {
  url: "/consent",
  heading: "Parental consent required",
  fields: [
    { id: "parent_name",  label: "Parent / guardian name"  },
    { id: "parent_email", label: "Parent / guardian email" },
  ],
  checkboxId: "consent",
  checkboxLabel: "I consent to my child using StudyBuddy and agree to the Privacy Policy.",
  submitButton: "Give consent",
} as const;

// ---------------------------------------------------------------------------
// PUB-28 — Reset Password Page (`/reset-password`)
// ---------------------------------------------------------------------------

export const RESET_PASSWORD = {
  url: "/reset-password",
  /** Default mode (no ?token param) */
  defaultHeading: "Reset your password",
  defaultSubtitle: "Enter your email and we'll send a reset link",
  emailFieldId: "email",
  submitButton: "Send reset link",
  /** Token mode (?token=xxx) */
  tokenUrl: "/reset-password?token=test-token-123",
  tokenHeading: "Set new password",
  tokenSubmitButton: "Set new password",
} as const;
