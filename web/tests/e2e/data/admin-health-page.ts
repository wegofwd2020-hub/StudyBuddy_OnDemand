/**
 * Test data for section 4.11 — System Health (`/admin/health`)
 * Covers TC-IDs: ADM-55, ADM-56, ADM-57, ADM-58, ADM-59, ADM-61
 */

import type { SystemHealth } from "@/lib/api/admin";

export const MOCK_HEALTH_OK: SystemHealth = {
  db_status:                 "ok",
  redis_status:              "ok",
  db_pool_size:              20,
  db_pool_available:         18,
  redis_connected_clients:   4,
  checked_at:                "2026-03-28T07:00:00Z",
};

export const MOCK_HEALTH_DEGRADED: SystemHealth = {
  db_status:    "error",
  redis_status: "ok",
  checked_at:   "2026-03-28T07:00:00Z",
};

export const HEALTH_STRINGS = {
  pageHeading:     "System Health",
  // Service rows
  postgresRow:     "PostgreSQL",
  redisRow:        "Redis",
  // Status banners
  allOkBanner:     "All systems operational",
  degradedBanner:  "One or more systems degraded",
} as const;
