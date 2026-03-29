/**
 * Test data for section 4.6 — Pipeline Trigger (`/admin/pipeline/trigger`)
 * Covers TC-IDs: ADM-21, ADM-22, ADM-23, ADM-24, ADM-25
 */

export const MOCK_PRODUCT_ADMIN = {
  admin_id: "adm-001",
  role: "product_admin" as const,
};

export const MOCK_DEVELOPER = {
  admin_id: "adm-002",
  role: "developer" as const,
};

export const MOCK_NEW_JOB = {
  job_id: "job-new-999",
};

export const TRIGGER_STRINGS = {
  pageHeading: "Trigger Pipeline Job",
  // Form fields
  gradeLabel: "Grade",
  languagesLabel: "Languages (comma-separated)",
  forceLabel: /Force regenerate/,
  // Buttons
  triggerBtn: "Trigger Job",
  triggeringBtn: "Triggering…",
  // Access denied
  accessDenied: "Access denied",
  // Error
  errorMsg: /Failed to trigger pipeline job/,
} as const;
