/**
 * Test data for section 4.13 — RBAC Sidebar Filtering
 * Covers TC-IDs: ADM-66, ADM-67, ADM-68, ADM-69, ADM-70
 */

export const MOCK_DEVELOPER = {
  admin_id: "adm-dev",
  role: "developer" as const,
};

export const MOCK_PRODUCT_ADMIN = {
  admin_id: "adm-pa",
  role: "product_admin" as const,
};

export const MOCK_SUPER_ADMIN = {
  admin_id: "adm-sa",
  role: "super_admin" as const,
};

export const ADMIN_NAV_STRINGS = {
  // Nav item labels that are RBAC-gated
  feedback: "Feedback",
  auditLog: "Audit Log",
  // Always-visible items
  dashboard: "Dashboard",
  analytics: "Analytics",
  pipeline: "Pipeline",
  contentReview: "Content Review",
  health: "Health",
  // Sign out
  signOut: "Sign out",
} as const;
