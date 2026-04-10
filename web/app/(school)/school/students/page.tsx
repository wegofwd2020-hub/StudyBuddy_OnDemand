"use client";

import { useState, useMemo } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTeacher } from "@/lib/hooks/useTeacher";
import { getRoster, uploadRoster, getSchoolProfile, listTeachers } from "@/lib/api/school-admin";
import { getClassMetrics } from "@/lib/api/reports";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Label } from "@/components/ui/label";
import { Copy, Check, Users, UserPlus, BookOpen } from "lucide-react";

function parseEmails(raw: string): string[] {
  return raw
    .split(/[\n,;]+/)
    .map((s) => s.trim().toLowerCase())
    .filter((s) => s.includes("@"));
}

const STATUS_STYLE: Record<string, string> = {
  active: "bg-green-50 text-green-700 border-green-200",
  invited: "bg-blue-50 text-blue-700 border-blue-100",
  pending: "bg-yellow-50 text-yellow-700 border-yellow-100",
};

function ProgressBar({ pct }: { pct: number }) {
  const clamped = Math.min(100, Math.max(0, pct));
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-20 overflow-hidden rounded-full bg-gray-100">
        <div
          className="h-full rounded-full bg-indigo-500"
          style={{ width: `${clamped}%` }}
        />
      </div>
      <span className="text-xs tabular-nums text-gray-500">{Math.round(clamped)}%</span>
    </div>
  );
}

// ── Teacher view (non-admin) ──────────────────────────────────────────────────

function TeacherStudentView({ schoolId, teacherId }: { schoolId: string; teacherId: string }) {
  // Get this teacher's assigned grades
  const { data: teachers, isLoading: loadingTeachers } = useQuery({
    queryKey: ["teachers", schoolId],
    queryFn: () => listTeachers(schoolId),
    enabled: !!schoolId,
    staleTime: 30_000,
  });

  const assignedGrades = useMemo(() => {
    if (!teachers) return null;
    const me = teachers.find((t) => t.teacher_id === teacherId);
    return me?.assigned_grades ?? [];
  }, [teachers, teacherId]);

  // Fetch class metrics (all grades — we'll filter on the frontend)
  const { data: metrics, isLoading: loadingMetrics } = useQuery({
    queryKey: ["class-metrics", schoolId],
    queryFn: () => getClassMetrics(schoolId),
    enabled: !!schoolId,
    staleTime: 60_000,
  });

  const students = useMemo(() => {
    if (!metrics) return [];
    if (!assignedGrades || assignedGrades.length === 0) return metrics.students;
    return metrics.students.filter((s) => assignedGrades.includes(s.grade));
  }, [metrics, assignedGrades]);

  const isLoading = loadingTeachers || loadingMetrics;

  return (
    <Card className="border shadow-sm">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-base">
          <BookOpen className="h-4 w-4 text-indigo-600" />
          My Students
          {assignedGrades && assignedGrades.length > 0 && (
            <span className="text-xs font-normal text-gray-400">
              — Grades {assignedGrades.join(", ")}
            </span>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        {isLoading ? (
          <div className="space-y-2 p-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-10 rounded" />
            ))}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-gray-50">
                  <th className="px-4 py-2.5 text-left text-xs font-medium text-gray-500">
                    Name
                  </th>
                  <th className="px-4 py-2.5 text-left text-xs font-medium text-gray-500">
                    Grade
                  </th>
                  <th className="px-4 py-2.5 text-left text-xs font-medium text-gray-500">
                    Progress
                  </th>
                  <th className="px-4 py-2.5 text-left text-xs font-medium text-gray-500">
                    Avg Score
                  </th>
                  <th className="px-4 py-2.5 text-left text-xs font-medium text-gray-500">
                    Last Active
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {students.map((s) => (
                  <tr key={s.student_id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium text-gray-800">{s.student_name}</td>
                    <td className="px-4 py-3 text-gray-600">Grade {s.grade}</td>
                    <td className="px-4 py-3">
                      <ProgressBar pct={(s.units_completed / Math.max(s.total_units, 1)) * 100} />
                    </td>
                    <td className="px-4 py-3 tabular-nums text-gray-600">
                      {s.avg_score_pct != null ? `${Math.round(s.avg_score_pct)}%` : "—"}
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-400">
                      {s.last_active ? new Date(s.last_active).toLocaleDateString() : "—"}
                    </td>
                  </tr>
                ))}
                {students.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-4 py-8 text-center text-sm text-gray-400">
                      {assignedGrades && assignedGrades.length === 0
                        ? "No grades assigned yet. Ask your school admin to assign grades to your account."
                        : "No students found for your assigned grades."}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ── Admin view ────────────────────────────────────────────────────────────────

function AdminStudentView({ schoolId }: { schoolId: string }) {
  const qc = useQueryClient();

  const { data: roster, isLoading: loadingRoster } = useQuery({
    queryKey: ["roster", schoolId],
    queryFn: () => getRoster(schoolId),
    enabled: !!schoolId,
    staleTime: 120_000,
  });

  const { data: profile } = useQuery({
    queryKey: ["school-profile", schoolId],
    queryFn: () => getSchoolProfile(schoolId),
    enabled: !!schoolId,
    staleTime: 300_000,
  });

  const [emailInput, setEmailInput] = useState("");
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<{
    enrolled: number;
    already_enrolled: number;
  } | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const inviteUrl =
    profile?.enrolment_code && typeof window !== "undefined"
      ? `${window.location.origin}/enrol/${profile.enrolment_code}`
      : null;

  function copyInviteLink() {
    if (!inviteUrl) return;
    navigator.clipboard.writeText(inviteUrl).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  async function handleUploadRoster() {
    const emails = parseEmails(emailInput);
    if (emails.length === 0 || !schoolId) return;
    setUploading(true);
    setUploadResult(null);
    setUploadError(null);
    try {
      const res = await uploadRoster(schoolId, emails);
      setUploadResult(res);
      setEmailInput("");
      await qc.invalidateQueries({ queryKey: ["roster", schoolId] });
    } catch {
      setUploadError("Failed to enrol students. Check the email list and try again.");
    } finally {
      setUploading(false);
    }
  }

  const emailCount = parseEmails(emailInput).length;

  return (
    <>
      {/* Invite link */}
      {inviteUrl && (
        <Card className="border shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Enrolment invite link</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="mb-2 text-xs text-gray-500">
              Share this link with students. They will be prompted to sign in and confirm
              enrolment.
            </p>
            <div className="flex items-center gap-2">
              <code className="flex-1 overflow-hidden rounded border bg-gray-50 px-3 py-2 font-mono text-xs text-ellipsis whitespace-nowrap text-gray-700">
                {inviteUrl}
              </code>
              <Button
                variant="outline"
                size="sm"
                onClick={copyInviteLink}
                className="h-9 shrink-0 gap-1.5"
              >
                {copied ? (
                  <Check className="h-3.5 w-3.5 text-green-500" />
                ) : (
                  <Copy className="h-3.5 w-3.5" />
                )}
                {copied ? "Copied" : "Copy"}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Bulk email enrol */}
      <Card className="border shadow-sm">
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-base">
            <UserPlus className="h-4 w-4 text-blue-600" />
            Bulk enrol by email
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="space-y-1.5">
            <Label htmlFor="email_list">Student email addresses</Label>
            <textarea
              id="email_list"
              value={emailInput}
              onChange={(e) => setEmailInput(e.target.value)}
              rows={4}
              placeholder="student1@school.edu&#10;student2@school.edu&#10;or comma-separated"
              className="w-full resize-none rounded-md border border-gray-200 px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
            />
            {emailCount > 0 && (
              <p className="text-xs text-gray-400">
                {emailCount} valid email{emailCount !== 1 ? "s" : ""} detected
              </p>
            )}
          </div>

          {uploadError && <p className="text-sm text-red-600">{uploadError}</p>}
          {uploadResult && (
            <div className="rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-700">
              <span className="font-semibold">{uploadResult.enrolled}</span> new student
              {uploadResult.enrolled !== 1 ? "s" : ""} enrolled.
              {uploadResult.already_enrolled > 0 && (
                <span className="text-gray-500">
                  {" "}
                  ({uploadResult.already_enrolled} already enrolled — skipped)
                </span>
              )}
            </div>
          )}

          <Button
            onClick={handleUploadRoster}
            disabled={uploading || emailCount === 0}
            className="gap-2"
          >
            {uploading
              ? "Enrolling…"
              : `Enrol ${emailCount > 0 ? emailCount : ""} student${emailCount !== 1 ? "s" : ""}`}
          </Button>
        </CardContent>
      </Card>

      {/* Roster table */}
      <Card className="border shadow-sm">
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Enrolled students</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {loadingRoster ? (
            <div className="space-y-2 p-4">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-10 rounded" />
              ))}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-gray-50">
                    <th className="px-4 py-2.5 text-left text-xs font-medium text-gray-500">
                      Email
                    </th>
                    <th className="px-4 py-2.5 text-left text-xs font-medium text-gray-500">
                      Status
                    </th>
                    <th className="px-4 py-2.5 text-left text-xs font-medium text-gray-500">
                      Added
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {(roster?.roster ?? []).map((item) => (
                    <tr key={item.student_email} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-gray-700">{item.student_email}</td>
                      <td className="px-4 py-3">
                        <Badge
                          className={`text-xs ${STATUS_STYLE[item.status] ?? "bg-gray-100 text-gray-500"}`}
                        >
                          {item.status}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 text-xs text-gray-400">
                        {new Date(item.added_at).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
                  {(roster?.roster ?? []).length === 0 && (
                    <tr>
                      <td
                        colSpan={3}
                        className="px-4 py-8 text-center text-sm text-gray-400"
                      >
                        No students enrolled yet.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function StudentsPage() {
  const teacher = useTeacher();
  const schoolId = teacher?.school_id ?? "";
  const isAdmin = teacher?.role === "school_admin";

  return (
    <div className="max-w-3xl space-y-6 p-6">
      <div className="flex items-center gap-3">
        <Users className="h-6 w-6 text-blue-600" />
        <h1 className="text-2xl font-bold text-gray-900">Student Roster</h1>
      </div>

      {isAdmin ? (
        <AdminStudentView schoolId={schoolId} />
      ) : schoolId && teacher?.teacher_id ? (
        <TeacherStudentView schoolId={schoolId} teacherId={teacher.teacher_id} />
      ) : null}
    </div>
  );
}
