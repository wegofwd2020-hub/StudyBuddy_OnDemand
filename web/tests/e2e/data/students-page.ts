/**
 * Test data for section 3.16 — Student Roster (`/school/students`)
 * Covers TC-IDs: SCH-35, SCH-36, SCH-37, SCH-38, SCH-39, SCH-40
 */

import type { RosterResponse, SchoolProfile } from "@/lib/api/school-admin";

export const MOCK_TEACHER = {
  teacher_id: "teacher-001",
  school_id: "school-001",
  role: "teacher" as const,
};

export const MOCK_ROSTER: RosterResponse = {
  roster: [
    {
      student_email: "alice@school.edu",
      student_id: "stu-001",
      status: "active",
      added_at: "2026-03-01T10:00:00Z",
    },
    {
      student_email: "ben@school.edu",
      student_id: "stu-002",
      status: "active",
      added_at: "2026-03-05T10:00:00Z",
    },
    {
      student_email: "charlie@school.edu",
      student_id: null,
      status: "invited",
      added_at: "2026-03-10T10:00:00Z",
    },
    {
      student_email: "diana@school.edu",
      student_id: null,
      status: "pending",
      added_at: "2026-03-15T10:00:00Z",
    },
  ],
};

export const MOCK_PROFILE: SchoolProfile = {
  school_id: "school-001",
  name: "Greenwood Academy",
  contact_email: "admin@greenwood.edu",
  country: "Canada",
  enrolment_code: "GWD-2026",
  status: "active",
  created_at: "2025-09-01T00:00:00Z",
};

export const STUDENTS_STRINGS = {
  pageHeading: "Student Roster",
  // Table column headers
  colEmail: "Email",
  colStatus: "Status",
  colAdded: "Added",
  // Invite link card
  inviteLinkHeading: "Enrolment invite link",
  copyBtn: "Copy",
  copiedBtn: "Copied",
  // Bulk enrol card
  bulkEnrolHeading: "Bulk enrol by email",
  emailListLabel: "Student email addresses",
  enrollBtn: /Enrol/,
  // Success message
  enrolledSuccess: /\d+ new students? enrolled/,
  // Empty state
  noStudents: "No students enrolled yet.",
} as const;

// Email inputs for bulk enrol tests
export const NEWLINE_EMAILS = "test1@school.edu\ntest2@school.edu\ntest3@school.edu";
export const COMMA_EMAILS = "test1@school.edu,test2@school.edu,test3@school.edu";
export const MIXED_EMAILS = "valid@school.edu\nnot-an-email\nanother@school.edu\njunk";
export const VALID_EMAIL_COUNT = 2; // from MIXED_EMAILS
