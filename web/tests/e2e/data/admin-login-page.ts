/**
 * Test data for section 4.1 — Admin Login (`/admin/login`)
 * Covers TC-IDs: ADM-01, ADM-02, ADM-03, ADM-04
 */

export const LOGIN_STRINGS = {
  pageHeading: "Sign in to admin console",
  emailLabel: "Email",
  passwordLabel: "Password",
  signInBtn: "Sign in",
  signingInBtn: "Signing in…",
  errorMsg: /Invalid credentials/,
} as const;

export const VALID_CREDENTIALS = {
  email: "admin@studybuddy.ca",
  password: "secret123",
  token:
    "eyJhbGciOiJIUzI1NiJ9.eyJhZG1pbl9pZCI6ImFkbS0wMDEiLCJyb2xlIjoicHJvZHVjdF9hZG1pbiJ9.sig",
  admin_id: "adm-001",
};
