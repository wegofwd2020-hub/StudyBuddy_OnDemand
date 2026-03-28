/**
 * Test data for section 2.15 — Enrolment Confirmation (`/enrol/[token]`)
 * Covers TC-IDs: STU-48, STU-49, STU-50
 *
 * Auth note: /enrol/[token] requires a real Auth0 session for E2E.
 * Unit tests mock confirmEnrolment() and useParams() directly.
 *
 * STU-48: Valid token → success state with school name displayed.
 * STU-49: Invalid/expired token → error message shown.
 * STU-50: Loading skeleton shown while confirmEnrolment() is pending.
 *
 * Backend API routes for E2E page.route() interception:
 *   POST /api/v1/school/enrol/confirm  (valid token)   → { school_name }
 *   POST /api/v1/school/enrol/confirm  (invalid token) → 400 { detail: "..." }
 */

// ---------------------------------------------------------------------------
// Test tokens
// ---------------------------------------------------------------------------

export const VALID_TOKEN   = "enrol-token-abc123";
export const INVALID_TOKEN = "enrol-token-bad999";

// ---------------------------------------------------------------------------
// Mock API responses
// ---------------------------------------------------------------------------

export const MOCK_ENROL_SUCCESS = {
  school_name: "Greenwood Academy",
};

export const MOCK_ENROL_ERROR_DETAIL = "This enrolment link is invalid or has expired.";

// ---------------------------------------------------------------------------
// Expected UI strings
// ---------------------------------------------------------------------------

export const ENROL_STRINGS = {
  // Success state
  successHeading:  "You're enrolled!",
  successBodyPart: "been successfully enrolled in",
  dashboardBtn:    "Go to dashboard",
  // Error state
  errorHeading:    "Enrolment failed",
  defaultError:    "This enrolment link is invalid or has expired.",
  backBtn:         "Back to dashboard",
} as const;

// ---------------------------------------------------------------------------
// Expected hrefs
// ---------------------------------------------------------------------------

export const ENROL_HREFS = {
  dashboard: "/dashboard",
} as const;
