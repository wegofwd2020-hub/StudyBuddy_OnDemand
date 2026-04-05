/**
 * Test data for section 4.8 — Content Review Queue (`/admin/content-review`)
 * Covers TC-IDs: ADM-31, ADM-32, ADM-33, ADM-34, ADM-35
 */

import type { ReviewQueueResponse } from "@/lib/api/admin";

export const MOCK_QUEUE: ReviewQueueResponse = {
  total: 2,
  items: [
    {
      version_id: "ver-001",
      curriculum_id: "default-2026-g8",
      subject: "Math",
      subject_name: "Mathematics",
      version_number: 1,
      status: "pending",
      alex_warnings_count: 0,
      generated_at: "2026-03-28T08:00:00Z",
      published_at: null,
      has_content: true,
      assigned_to_admin_id: null,
      assigned_to_email: null,
      assigned_at: null,
    },
    {
      version_id: "ver-002",
      curriculum_id: "default-2026-g7",
      subject: "Biology",
      subject_name: "Biology",
      version_number: 2,
      status: "pending",
      alex_warnings_count: 0,
      generated_at: "2026-03-27T08:00:00Z",
      published_at: null,
      has_content: true,
      assigned_to_admin_id: null,
      assigned_to_email: null,
      assigned_at: null,
    },
  ],
};

export const MOCK_QUEUE_EMPTY: ReviewQueueResponse = { total: 0, items: [] };

export const REVIEW_QUEUE_STRINGS = {
  pageHeading: "Content Review Queue",
  // Filter tabs
  tabPending: "pending",
  tabApproved: "approved",
  tabPublished: "published",
  tabRejected: "rejected",
  tabBlocked: "blocked",
  tabAll: "All",
  // Table columns
  colUnit: "Unit",
  colGrade: "Grade",
  colLang: "Lang",
  colStatus: "Status",
  // Review link
  reviewLink: "Review →",
  // Empty state
  noItems: /No .* items in the queue/,
} as const;
