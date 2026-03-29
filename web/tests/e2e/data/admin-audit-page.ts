/**
 * Test data for section 4.12 — Audit Log (`/admin/audit`)
 * Covers TC-IDs: ADM-62, ADM-63, ADM-64, ADM-65
 */

import type { AuditLogResponse } from "@/lib/api/admin";

export const MOCK_PRODUCT_ADMIN = {
  admin_id: "adm-001",
  role: "product_admin" as const,
};

export const MOCK_DEVELOPER = {
  admin_id: "adm-002",
  role: "developer" as const,
};

export const MOCK_AUDIT_LOG: AuditLogResponse = {
  total: 3,
  page: 1,
  page_size: 50,
  entries: [
    {
      audit_id: "aud-001",
      actor_id: "adm-001-xxxx",
      actor_role: "product_admin",
      action: "publish",
      resource_type: "content_version",
      resource_id: "ver-001-xxxx-xxxx",
      detail: {},
      created_at: "2026-03-28T08:00:00Z",
    },
    {
      audit_id: "aud-002",
      actor_id: "adm-001-xxxx",
      actor_role: "product_admin",
      action: "approve",
      resource_type: "content_version",
      resource_id: "ver-002-xxxx-xxxx",
      detail: {},
      created_at: "2026-03-27T08:00:00Z",
    },
  ],
};

// 51 entries to test pagination
export const MOCK_AUDIT_LOG_PAGE1: AuditLogResponse = {
  total: 51,
  page: 1,
  page_size: 50,
  entries: Array.from({ length: 50 }, (_, i) => ({
    audit_id: `aud-p${i}`,
    actor_id: "adm-001-xxxx",
    actor_role: "product_admin",
    action: "approve",
    resource_type: "content_version",
    resource_id: `ver-${i}-xxxx`,
    detail: {},
    created_at: "2026-03-28T08:00:00Z",
  })),
};

export const AUDIT_STRINGS = {
  pageHeading: "Audit Log",
  // Table column headers
  colTime: "Time",
  colActor: "Actor",
  colAction: "Action",
  colResource: "Resource",
  // Filter input placeholder
  filterPlaceholder: /Filter by action/,
  // Pagination
  nextBtn: "Next",
  prevBtn: "Previous",
  // Access denied
  accessDenied: "Access denied",
} as const;
