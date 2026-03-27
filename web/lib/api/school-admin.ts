import schoolApi from "./school-client";

// ── School profile ────────────────────────────────────────────────────────────

export interface SchoolProfile {
  school_id: string;
  name: string;
  contact_email: string;
  country: string;
  enrolment_code: string | null;
  status: string;
  created_at: string;
}

export async function getSchoolProfile(schoolId: string): Promise<SchoolProfile> {
  const res = await schoolApi.get<SchoolProfile>(`/schools/${schoolId}`);
  return res.data;
}

// ── Roster ────────────────────────────────────────────────────────────────────

export interface RosterItem {
  student_email: string;
  student_id: string | null;
  status: string;
  added_at: string;
}

export interface RosterResponse {
  roster: RosterItem[];
}

export async function getRoster(schoolId: string): Promise<RosterResponse> {
  const res = await schoolApi.get<RosterResponse>(`/schools/${schoolId}/enrolment`);
  return res.data;
}

export interface EnrolmentUploadResponse {
  enrolled: number;
  already_enrolled: number;
}

export async function uploadRoster(
  schoolId: string,
  studentEmails: string[],
): Promise<EnrolmentUploadResponse> {
  const res = await schoolApi.post<EnrolmentUploadResponse>(
    `/schools/${schoolId}/enrolment`,
    { student_emails: studentEmails },
  );
  return res.data;
}

// ── Teachers ──────────────────────────────────────────────────────────────────

export interface TeacherInviteResponse {
  teacher_id: string;
  email: string;
  role: string;
}

export async function inviteTeacher(
  schoolId: string,
  name: string,
  email: string,
): Promise<TeacherInviteResponse> {
  const res = await schoolApi.post<TeacherInviteResponse>(
    `/schools/${schoolId}/teachers/invite`,
    { name, email },
  );
  return res.data;
}
