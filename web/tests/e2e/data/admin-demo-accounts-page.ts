/**
 * Test data for Demo Accounts admin page (`/admin/demo-accounts`)
 * Covers TC-IDs: ADM-60, ADM-61, ADM-62, ADM-63, ADM-64, ADM-65
 */

import type { DemoAccountListResponse } from "@/lib/api/admin";

export const MOCK_PRODUCT_ADMIN = {
  admin_id: "adm-001",
  role: "product_admin" as const,
};

export const MOCK_DEVELOPER = {
  admin_id: "adm-002",
  role: "developer" as const,
};

export const MOCK_ACTIVE_ITEM = {
  request_id: "req-001",
  email: "alice@example.com",
  request_status: "verified" as const,
  account_id: "acct-001",
  expires_at: new Date(Date.now() + 20 * 60 * 60 * 1_000).toISOString(),
  revoked_at: null,
  extended_at: null,
  verification_pending: false,
};

export const MOCK_PENDING_ITEM = {
  request_id: "req-002",
  email: "bob@example.com",
  request_status: "pending" as const,
  account_id: null,
  expires_at: null,
  revoked_at: null,
  extended_at: null,
  verification_pending: true,
};

export const MOCK_REVOKED_ITEM = {
  request_id: "req-003",
  email: "carol@example.com",
  request_status: "revoked" as const,
  account_id: "acct-002",
  expires_at: null,
  revoked_at: "2026-03-29T10:00:00Z",
  extended_at: null,
  verification_pending: false,
};

export const MOCK_DEMO_LIST: DemoAccountListResponse = {
  total: 3,
  page: 1,
  page_size: 20,
  items: [MOCK_ACTIVE_ITEM, MOCK_PENDING_ITEM, MOCK_REVOKED_ITEM],
};

// 21 items to test pagination (Next button enabled)
export const MOCK_DEMO_LIST_PAGE1: DemoAccountListResponse = {
  total: 21,
  page: 1,
  page_size: 20,
  items: Array.from({ length: 20 }, (_, i) => ({
    request_id: `req-p${i}`,
    email: `student${i}@example.com`,
    request_status: "verified" as const,
    account_id: `acct-p${i}`,
    expires_at: new Date(Date.now() + 24 * 60 * 60 * 1_000).toISOString(),
    revoked_at: null,
    extended_at: null,
    verification_pending: false,
  })),
};

export const MOCK_EMPTY_LIST: DemoAccountListResponse = {
  total: 0,
  page: 1,
  page_size: 20,
  items: [],
};

export const DEMO_ACCOUNTS_STRINGS = {
  pageHeading: "Demo Accounts",
  accessDenied: "Access denied",
  extendBtn: "Extend",
  revokeBtn: "Revoke",
  resendBtn: "Resend",
  nextBtn: "Next",
  prevBtn: "Previous",
  confirmRevokeBtn: "Revoke",
  cancelBtn: "Cancel",
  emptyMsg: "No demo accounts found.",
} as const;
