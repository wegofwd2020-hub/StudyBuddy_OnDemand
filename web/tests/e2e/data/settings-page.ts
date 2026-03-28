/**
 * Test data for section 3.18 — School Settings (`/school/settings`)
 * Covers TC-IDs: SCH-45, SCH-46, SCH-47, SCH-48
 */

import type { SchoolProfile } from "@/lib/api/school-admin";

export const MOCK_ADMIN = {
  teacher_id: "teacher-001",
  school_id:  "school-001",
  role: "school_admin" as const,
};

export const MOCK_TEACHER = {
  teacher_id: "teacher-002",
  school_id:  "school-001",
  role: "teacher" as const,
};

export const MOCK_PROFILE: SchoolProfile = {
  school_id:      "school-001",
  name:           "Greenwood Academy",
  contact_email:  "admin@greenwood.edu",
  country:        "Canada",
  enrolment_code: "GWD-2026",
  status:         "active",
  created_at:     "2025-09-01T00:00:00Z",
};

export const SETTINGS_STRINGS = {
  pageHeading:      "School Settings",
  // Profile card
  profileCard:      "School profile",
  schoolName:       MOCK_PROFILE.name,
  contactEmail:     MOCK_PROFILE.contact_email,
  country:          MOCK_PROFILE.country,
  status:           MOCK_PROFILE.status,
  schoolId:         MOCK_PROFILE.school_id,
  // Enrolment code card
  enrolmentCard:    "Enrolment code",
  enrolmentCode:    MOCK_PROFILE.enrolment_code!,
  copyBtn:          "Copy",
  copiedBtn:        "Copied",
  // Billing card (admin only)
  billingCard:      "Billing",
  billingPortalBtn: "Open billing portal",
  // Non-admin message
  contactAdmin:     "Contact your school administrator to update school details.",
} as const;
