/**
 * Test data for section 4.9 — Content Review Detail (`/admin/content-review/[version_id]`)
 * Covers TC-IDs: ADM-36..ADM-49
 */

import type { ReviewItemDetail } from "@/lib/api/admin";

export const MOCK_VERSION_ID = "ver-001";

const BASE_ITEM = {
  // ReviewQueueItem fields
  version_id: MOCK_VERSION_ID,
  curriculum_id: "default-2026-g8",
  subject: "Math",
  subject_name: "Mathematics",
  version_number: 1,
  alex_warnings_count: 0,
  generated_at: "2026-03-28T08:00:00Z",
  published_at: null as string | null,
  has_content: true,
  assigned_to_admin_id: null as string | null,
  assigned_to_email: null as string | null,
  assigned_at: null as string | null,
  provider: "anthropic" as const,
  // ReviewItemDetail extras
  units: [{ unit_id: "unit-001", title: "Algebra Basics", sort_order: 1 }],
  review_history: [],
};

export const MOCK_ITEM_PENDING: ReviewItemDetail = {
  ...BASE_ITEM,
  status: "pending",
  annotations: [],
};

export const MOCK_ITEM_APPROVED: ReviewItemDetail = {
  ...BASE_ITEM,
  status: "approved",
  annotations: [],
};

export const MOCK_ITEM_PUBLISHED: ReviewItemDetail = {
  ...BASE_ITEM,
  status: "published",
  annotations: [],
};

export const MOCK_ITEM_WITH_ANNOTATIONS: ReviewItemDetail = {
  ...BASE_ITEM,
  status: "pending",
  annotations: [
    {
      annotation_id: "ann-001",
      unit_id: "unit-001",
      content_type: "lesson",
      annotation_text: "Please simplify the language in paragraph 2.",
      created_at: "2026-03-27T10:00:00Z",
      reviewer_email: "admin@example.com",
    },
  ],
};

export const MOCK_PRODUCT_ADMIN = {
  admin_id: "adm-001",
  role: "product_admin" as const,
};

export const MOCK_DEVELOPER = {
  admin_id: "adm-002",
  role: "developer" as const,
};

export const REVIEW_DETAIL_STRINGS = {
  backLink: "Back to queue",
  // Metadata
  lessonPreview: "Lesson Preview",
  // Actions — pending
  approveBtn: "Approve",
  rejectBtn: "Reject",
  // Actions — approved (product_admin)
  publishBtn: "Publish",
  // Actions — published (product_admin)
  rollbackBtn: "Rollback",
  blockBtn: "Block",
  // Modal
  confirmReject: "Confirm reject",
  confirmBlock: "Confirm block",
  // Annotations — component renders "Annotations (N)" with the count
  annotationsHeading: "Annotations (1)",
} as const;
