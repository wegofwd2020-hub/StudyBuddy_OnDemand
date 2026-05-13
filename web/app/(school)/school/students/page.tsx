"use client";

import { useState, useMemo } from "react";
import { useQuery, useQueries, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTeacher } from "@/lib/hooks/useTeacher";
import {
  getRoster,
  uploadRoster,
  getSchoolProfile,
  listClassrooms,
  getClassroom,
  provisionStudent,
  resetStudentPassword,
  type RosterItem,
} from "@/lib/api/school-admin";
import { getClassMetrics } from "@/lib/api/reports";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Copy, Check, Users, UserPlus, BookOpen, KeyRound } from "lucide-react";
import { cn } from "@/lib/utils";

type ScopeFilter = "mine" | "all";

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
      <span className="text-xs text-gray-500 tabular-nums">{Math.round(clamped)}%</span>
    </div>
  );
}

// ── Teacher view (non-admin) ──────────────────────────────────────────────────

function TeacherStudentView({
  schoolId,
  teacherId,
}: {
  schoolId: string;
  teacherId: string;
}) {
  const [scope, setScope] = useState<ScopeFilter>("mine");
  const [gradeFilter, setGradeFilter] = useState<number | "">("");

  // School-wide metrics fuels the table rows; scope (mine/all) is applied
  // client-side using the classroom_students of classrooms the user leads.
  const { data: metrics, isLoading: loadingMetrics } = useQuery({
    queryKey: ["class-metrics", schoolId],
    queryFn: () => getClassMetrics(schoolId),
    enabled: !!schoolId,
    staleTime: 60_000,
  });

  // Look up which classrooms the logged-in teacher leads so we can compute
  // "my students" = students enrolled in any of those classrooms.
  const { data: classrooms, isLoading: loadingClassrooms } = useQuery({
    queryKey: ["classrooms", schoolId],
    queryFn: () => listClassrooms(schoolId),
    enabled: !!schoolId,
    staleTime: 60_000,
  });
  const myClassrooms = (classrooms ?? []).filter((c) => c.teacher_id === teacherId);

  // Pull per-classroom rosters in parallel — listClassrooms only returns
  // counts; getClassroom returns the full students array.
  const myClassroomDetails = useQueries({
    queries: myClassrooms.map((c) => ({
      queryKey: ["classroom-detail", schoolId, c.classroom_id],
      queryFn: () => getClassroom(schoolId, c.classroom_id),
      enabled: !!schoolId,
      staleTime: 60_000,
    })),
  });

  const myStudentIds = useMemo(() => {
    const ids = new Set<string>();
    for (const q of myClassroomDetails) {
      for (const s of q.data?.students ?? []) {
        ids.add(s.student_id);
      }
    }
    return ids;
  }, [myClassroomDetails]);

  const myCount = myStudentIds.size;
  const effectiveScope: ScopeFilter = scope === "mine" && myCount === 0 ? "all" : scope;

  // Apply scope first, then grade.
  const scopedStudents = useMemo(() => {
    if (!metrics) return [];
    return metrics.students.filter((s) => {
      const scopeOk = effectiveScope === "all" || myStudentIds.has(s.student_id);
      const gradeOk = gradeFilter === "" || s.grade === gradeFilter;
      return scopeOk && gradeOk;
    });
  }, [metrics, effectiveScope, myStudentIds, gradeFilter]);

  // Grade pills derived from the current scope, not all students.
  const presentGrades = useMemo(() => {
    if (!metrics) return [];
    const base =
      effectiveScope === "all"
        ? metrics.students
        : metrics.students.filter((s) => myStudentIds.has(s.student_id));
    return [...new Set(base.map((s) => s.grade))].sort((a, b) => a - b);
  }, [metrics, effectiveScope, myStudentIds]);

  const isLoading = loadingMetrics || loadingClassrooms;
  const allCount = metrics?.students.length ?? 0;

  return (
    <Card className="border shadow-sm">
      <CardHeader className="pb-2">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <BookOpen className="h-4 w-4 text-indigo-600" />
            Students
          </CardTitle>

          {allCount > 0 && (
            <div className="flex flex-wrap items-center gap-3">
              {/* Scope toggle — default to "My students" (students enrolled in
                  classrooms the user leads). Auto-collapses to "All" if the
                  user leads no rosters yet. */}
              <div className="inline-flex rounded-md border border-gray-200 bg-gray-50 p-0.5 text-xs font-medium">
                <button
                  type="button"
                  onClick={() => setScope("mine")}
                  disabled={myCount === 0}
                  className={cn(
                    "rounded px-2.5 py-1 transition-colors",
                    effectiveScope === "mine"
                      ? "bg-white text-indigo-700 shadow-sm"
                      : "text-gray-500 hover:text-gray-700",
                    myCount === 0 && "cursor-not-allowed opacity-40",
                  )}
                  title={
                    myCount === 0
                      ? "You aren't the lead of any classrooms with students."
                      : undefined
                  }
                >
                  My students ({myCount})
                </button>
                <button
                  type="button"
                  onClick={() => setScope("all")}
                  className={cn(
                    "rounded px-2.5 py-1 transition-colors",
                    effectiveScope === "all"
                      ? "bg-white text-indigo-700 shadow-sm"
                      : "text-gray-500 hover:text-gray-700",
                  )}
                >
                  All school ({allCount})
                </button>
              </div>

              {presentGrades.length > 0 && (
                <div className="flex items-center gap-1.5">
                  <span className="text-xs text-gray-500">Grade:</span>
                  <button
                    type="button"
                    onClick={() => setGradeFilter("")}
                    className={cn(
                      "rounded px-2 py-1 text-xs font-medium transition-colors",
                      gradeFilter === ""
                        ? "bg-blue-600 text-white"
                        : "border bg-white text-gray-500 hover:text-gray-900",
                    )}
                  >
                    All
                  </button>
                  {presentGrades.map((g) => (
                    <button
                      type="button"
                      key={g}
                      onClick={() => setGradeFilter(g === gradeFilter ? "" : g)}
                      className={cn(
                        "rounded px-2 py-1 text-xs font-medium transition-colors",
                        gradeFilter === g
                          ? "bg-blue-600 text-white"
                          : "border bg-white text-gray-500 hover:text-gray-900",
                      )}
                    >
                      {g}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
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
                {scopedStudents.map((s) => (
                  <tr key={s.student_id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium text-gray-800">
                      {s.student_name}
                    </td>
                    <td className="px-4 py-3 text-gray-600">Grade {s.grade}</td>
                    <td className="px-4 py-3">
                      <ProgressBar
                        pct={(s.units_completed / Math.max(s.total_units, 1)) * 100}
                      />
                    </td>
                    <td className="px-4 py-3 text-gray-600 tabular-nums">
                      {s.avg_score_pct != null ? `${Math.round(s.avg_score_pct)}%` : "—"}
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-400">
                      {s.last_active ? new Date(s.last_active).toLocaleDateString() : "—"}
                    </td>
                  </tr>
                ))}
                {scopedStudents.length === 0 && (
                  <tr>
                    <td
                      colSpan={5}
                      className="px-4 py-8 text-center text-sm text-gray-400"
                    >
                      {effectiveScope === "mine"
                        ? 'No students in classrooms you lead. Switch to "All school" to browse the wider roster.'
                        : gradeFilter !== ""
                          ? `No Grade ${gradeFilter} students at this school.`
                          : "No students enrolled yet."}
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

// ── Roster row with reset password ───────────────────────────────────────────

function RosterRow({ item, schoolId }: { item: RosterItem; schoolId: string }) {
  const [confirmReset, setConfirmReset] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [tempPassword, setTempPassword] = useState<string | null>(null);

  const { mutate: doReset, isPending: resetting } = useMutation({
    mutationFn: () => resetStudentPassword(schoolId, item.student_id!),
    onSuccess: (data) => {
      setConfirmReset(false);
      setTempPassword(data.temp_password);
      setMsg(null);
    },
    onError: () => {
      setConfirmReset(false);
      setMsg("Reset failed. Please try again.");
    },
  });

  return (
    <>
      <tr className="hover:bg-gray-50">
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
        <td className="px-4 py-3">
          {item.student_id && item.status === "active" && (
            <button
              type="button"
              onClick={() => {
                setConfirmReset(true);
                setMsg(null);
              }}
              className="rounded-md p-1 text-gray-400 hover:bg-amber-50 hover:text-amber-600"
              aria-label="Reset password"
              title="Reset password"
            >
              <KeyRound className="h-3.5 w-3.5" />
            </button>
          )}
        </td>
      </tr>
      {confirmReset && (
        <tr>
          <td colSpan={4} className="bg-amber-50 px-4 py-3">
            <p className="mb-2 text-xs text-amber-800">
              Reset password for <strong>{item.student_email}</strong>? A new temporary
              password will be emailed to them.
            </p>
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="outline"
                className="h-7 border-amber-300 text-xs text-amber-700 hover:bg-amber-100"
                onClick={() => doReset()}
                disabled={resetting}
              >
                {resetting ? "Resetting…" : "Yes, reset"}
              </Button>
              <Button
                size="sm"
                variant="ghost"
                className="h-7 text-xs"
                onClick={() => setConfirmReset(false)}
                disabled={resetting}
              >
                Cancel
              </Button>
            </div>
          </td>
        </tr>
      )}
      {tempPassword && (
        <tr>
          <td colSpan={4} className="bg-green-50 px-4 py-3">
            <p className="mb-1 text-xs font-medium text-green-800">
              Password reset — share this with the student:
            </p>
            <div className="flex items-center gap-2">
              <code className="rounded border border-green-200 bg-white px-3 py-1.5 font-mono text-sm font-semibold tracking-wide text-green-900">
                {tempPassword}
              </code>
              <button
                type="button"
                onClick={() => navigator.clipboard.writeText(tempPassword)}
                className="text-xs text-green-700 underline hover:no-underline"
              >
                Copy
              </button>
              <button
                type="button"
                onClick={() => setTempPassword(null)}
                className="ml-2 text-xs text-green-600 underline hover:no-underline"
              >
                Dismiss
              </button>
            </div>
            <p className="mt-1 text-xs text-green-700">
              They will be required to set a new password on first login.
            </p>
          </td>
        </tr>
      )}
      {msg && (
        <tr>
          <td colSpan={4} className="bg-gray-50 px-4 py-2 text-xs text-gray-600">
            {msg}
          </td>
        </tr>
      )}
    </>
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

  // Add individual student
  const [addName, setAddName] = useState("");
  const [addEmail, setAddEmail] = useState("");
  const [addGrade, setAddGrade] = useState<string>("8");
  const [addError, setAddError] = useState<string | null>(null);
  const [addSuccess, setAddSuccess] = useState<string | null>(null);

  const { mutate: doProvision, isPending: provisioning } = useMutation({
    mutationFn: () =>
      provisionStudent(schoolId, {
        name: addName,
        email: addEmail,
        grade: Number(addGrade),
      }),
    onSuccess: (res) => {
      setAddSuccess(res.email);
      setAddName("");
      setAddEmail("");
      setAddGrade("8");
      qc.invalidateQueries({ queryKey: ["roster", schoolId] });
    },
    onError: (err: unknown) => {
      const status = (err as { response?: { status?: number } })?.response?.status;
      if (status === 409) {
        setAddError("A student with that email already exists.");
      } else if (status === 422) {
        setAddError("Invalid grade — must be between 1 and 12.");
      } else {
        setAddError("Could not add student. Please try again.");
      }
    },
  });

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

      {/* Add individual student */}
      <Card className="border shadow-sm">
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-base">
            <UserPlus className="h-4 w-4 text-indigo-600" />
            Add a student
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-3 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="student_name">Full name</Label>
              <Input
                id="student_name"
                value={addName}
                onChange={(e) => setAddName(e.target.value)}
                placeholder="Alex Johnson"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="student_email">Email</Label>
              <Input
                id="student_email"
                type="email"
                value={addEmail}
                onChange={(e) => {
                  setAddEmail(e.target.value);
                  setAddError(null);
                }}
                placeholder="alex@school.edu"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="student_grade">Grade</Label>
              <select
                id="student_grade"
                value={addGrade}
                onChange={(e) => setAddGrade(e.target.value)}
                className="h-9 w-full rounded-md border border-gray-200 bg-white px-3 text-sm focus:ring-2 focus:ring-indigo-500 focus:outline-none"
              >
                {[5, 6, 7, 8, 9, 10, 11, 12].map((g) => (
                  <option key={g} value={g}>
                    Grade {g}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {addError && <p className="text-sm text-red-600">{addError}</p>}
          {addSuccess && (
            <div className="flex items-center gap-2 rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-700">
              <Check className="h-4 w-4 shrink-0" />
              Student added. A temporary password has been sent to{" "}
              <span className="font-medium">{addSuccess}</span>. They must set a new
              password on first login.
            </div>
          )}

          <Button
            onClick={() => {
              setAddError(null);
              setAddSuccess(null);
              doProvision();
            }}
            disabled={provisioning || !addName || !addEmail}
            className="gap-2"
          >
            {provisioning ? "Adding…" : "Add student"}
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
                    <th className="px-4 py-2.5 text-left text-xs font-medium text-gray-500">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {(roster?.roster ?? []).map((item) => (
                    <RosterRow key={item.student_email} item={item} schoolId={schoolId} />
                  ))}
                  {(roster?.roster ?? []).length === 0 && (
                    <tr>
                      <td
                        colSpan={4}
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
