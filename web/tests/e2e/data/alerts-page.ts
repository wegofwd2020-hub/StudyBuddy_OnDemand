/**
 * Test data for section 3.12 — Alerts (`/school/alerts`)
 * Covers TC-IDs: SCH-19, SCH-20, SCH-21
 */

import type { AlertListResponse } from "@/lib/api/reports";

export const MOCK_TEACHER = {
  teacher_id: "teacher-001",
  school_id: "school-001",
  role: "teacher" as const,
};

export const MOCK_ALERTS: AlertListResponse = {
  alerts: [
    {
      alert_id: "alert-001",
      alert_type: "pass_rate_low",
      school_id: "school-001",
      details: { unit_id: "G8-MATH-002", pass_rate: 38 },
      triggered_at: "2026-03-27T08:00:00Z",
      acknowledged: false,
    },
    {
      alert_id: "alert-002",
      alert_type: "inactive_students",
      school_id: "school-001",
      details: { inactive_count: 5 },
      triggered_at: "2026-03-26T08:00:00Z",
      acknowledged: false,
    },
    {
      alert_id: "alert-003",
      alert_type: "score_drop",
      school_id: "school-001",
      details: { unit_id: "G8-SCI-003", score_drop: 12 },
      triggered_at: "2026-03-25T08:00:00Z",
      acknowledged: true,
    },
  ],
};

export const MOCK_ALERTS_EMPTY: AlertListResponse = { alerts: [] };

export const ALERTS_STRINGS = {
  pageHeading: "Alert Inbox",
  newBadge: /\d+ new/,
  // Alert type labels (from alertLabel function in page)
  lowPassRate: "Low pass rate",
  inactiveStudents: "Inactive students",
  scoreDrop: "Score drop",
  // Dismiss button
  dismissBtn: "Dismiss",
  // Acknowledged section
  acknowledgedLabel: "Acknowledged",
  // Empty state
  noAlerts: "No new alerts — all clear.",
} as const;
