"use client";

import { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTeacher } from "@/lib/hooks/useTeacher";
import {
  listTeachers,
  assignTeacherGrades,
  provisionTeacher,
  resetTeacherPassword,
  promoteTeacher,
  setTeacherCapabilities,
  CURRICULUM_CAPABILITIES,
  type TeacherRosterItem,
} from "@/lib/api/school-admin";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  GraduationCap,
  UserPlus,
  Check,
  ShieldCheck,
  Pencil,
  X,
  KeyRound,
  Crown,
  BookMarked,
} from "lucide-react";

const ALL_GRADES = [5, 6, 7, 8, 9, 10, 11, 12];

const CAP_LABELS: Record<string, string> = {
  "curriculum.commission": "Commission",
  "curriculum.review": "Review",
  curriculum_mgmt: "Curriculum Mgmt",
};

// ── Grade badge chip ──────────────────────────────────────────────────────────

function GradeChip({ grade }: { grade: number }) {
  return (
    <span className="inline-flex items-center rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-700">
      Gr {grade}
    </span>
  );
}

// ── Inline grade editor ───────────────────────────────────────────────────────

function GradeEditor({
  teacherId,
  schoolId,
  current,
  onDone,
}: {
  teacherId: string;
  schoolId: string;
  current: number[];
  onDone: () => void;
}) {
  const queryClient = useQueryClient();
  const [selected, setSelected] = useState<Set<number>>(new Set(current));
  const [error, setError] = useState<string | null>(null);

  const { mutate, isPending } = useMutation({
    mutationFn: () => assignTeacherGrades(schoolId, teacherId, [...selected]),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["teachers", schoolId] });
      onDone();
    },
    onError: () => setError("Failed to save. Please try again."),
  });

  function toggle(grade: number) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(grade)) {
        next.delete(grade);
      } else {
        next.add(grade);
      }
      return next;
    });
  }

  return (
    <div className="mt-2 rounded-lg border border-indigo-100 bg-indigo-50 p-3">
      <p className="mb-2 text-xs font-medium text-gray-600">Assign grades:</p>
      <div className="flex flex-wrap gap-1.5">
        {ALL_GRADES.map((g) => (
          <button
            key={g}
            type="button"
            onClick={() => toggle(g)}
            className={`rounded-full px-2.5 py-1 text-xs font-medium transition-colors ${
              selected.has(g)
                ? "bg-indigo-600 text-white"
                : "bg-white text-gray-600 ring-1 ring-gray-200 hover:bg-gray-50"
            }`}
          >
            Grade {g}
          </button>
        ))}
      </div>
      {error && <p className="mt-2 text-xs text-red-600">{error}</p>}
      <div className="mt-3 flex gap-2">
        <Button size="sm" onClick={() => mutate()} disabled={isPending}>
          {isPending ? "Saving…" : "Save"}
        </Button>
        <Button size="sm" variant="outline" onClick={onDone} disabled={isPending}>
          Cancel
        </Button>
      </div>
    </div>
  );
}

// ── Inline capability editor (issue #358) ────────────────────────────────────

function CapabilityEditor({
  teacherId,
  schoolId,
  current,
  onDone,
}: {
  teacherId: string;
  schoolId: string;
  current: string[];
  onDone: () => void;
}) {
  const queryClient = useQueryClient();
  const [selected, setSelected] = useState<Set<string>>(new Set(current));
  const [error, setError] = useState<string | null>(null);

  const { mutate, isPending } = useMutation({
    mutationFn: () => setTeacherCapabilities(schoolId, teacherId, [...selected]),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["teachers", schoolId] });
      onDone();
    },
    onError: () => setError("Failed to save. Please try again."),
  });

  function toggle(cap: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(cap)) next.delete(cap);
      else next.add(cap);
      return next;
    });
  }

  return (
    <div className="mt-2 rounded-lg border border-blue-100 bg-blue-50 p-3">
      <p className="mb-2 text-xs font-medium text-gray-600">
        Curriculum capabilities — grant the two gates separately for maker-checker, or the
        umbrella for both:
      </p>
      <div className="space-y-1.5">
        {CURRICULUM_CAPABILITIES.map((c) => (
          <label key={c.value} className="flex items-center gap-2 text-sm text-gray-700">
            <input
              type="checkbox"
              checked={selected.has(c.value)}
              onChange={() => toggle(c.value)}
              className="h-4 w-4 rounded border-gray-300 text-blue-600"
            />
            {c.label}
          </label>
        ))}
      </div>
      {error && <p className="mt-2 text-xs text-red-600">{error}</p>}
      <div className="mt-3 flex gap-2">
        <Button size="sm" onClick={() => mutate()} disabled={isPending}>
          {isPending ? "Saving…" : "Save"}
        </Button>
        <Button size="sm" variant="outline" onClick={onDone} disabled={isPending}>
          Cancel
        </Button>
      </div>
    </div>
  );
}

// ── Teacher row ───────────────────────────────────────────────────────────────

function TeacherRow({
  item,
  schoolId,
  isAdmin,
}: {
  item: TeacherRosterItem;
  schoolId: string;
  isAdmin: boolean;
}) {
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [editingCaps, setEditingCaps] = useState(false);
  const [confirmReset, setConfirmReset] = useState(false);
  const [confirmPromote, setConfirmPromote] = useState(false);
  const [actionMsg, setActionMsg] = useState<string | null>(null);
  const [tempPassword, setTempPassword] = useState<string | null>(null);

  const { mutate: doReset, isPending: resetting } = useMutation({
    mutationFn: () => resetTeacherPassword(schoolId, item.teacher_id),
    onSuccess: (data) => {
      setConfirmReset(false);
      setTempPassword(data.temp_password);
      setActionMsg(null);
    },
    onError: () => {
      setConfirmReset(false);
      setActionMsg("Reset failed. Please try again.");
    },
  });

  const { mutate: doPromote, isPending: promoting } = useMutation({
    mutationFn: () => promoteTeacher(schoolId, item.teacher_id),
    onSuccess: () => {
      setConfirmPromote(false);
      queryClient.invalidateQueries({ queryKey: ["teachers", schoolId] });
    },
    onError: () => {
      setConfirmPromote(false);
      setActionMsg("Promotion failed. Please try again.");
    },
  });

  return (
    <div className="rounded-lg border bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="font-medium text-gray-900">{item.name}</span>
            {item.role === "school_admin" ? (
              <span className="flex items-center gap-1 rounded-full bg-purple-50 px-2 py-0.5 text-xs font-medium text-purple-700">
                <ShieldCheck className="h-3 w-3" />
                Admin
              </span>
            ) : (
              <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-500">
                Teacher
              </span>
            )}
            {item.account_status === "pending" && (
              <Badge className="border-yellow-100 bg-yellow-50 text-xs text-yellow-700">
                Pending
              </Badge>
            )}
          </div>
          <p className="mt-0.5 text-sm text-gray-500">{item.email}</p>

          {/* Assigned grades */}
          <div className="mt-2 flex flex-wrap items-center gap-1.5">
            {item.assigned_grades.length > 0 ? (
              item.assigned_grades.map((g) => <GradeChip key={g} grade={g} />)
            ) : (
              <span className="text-xs text-gray-400 italic">No grades assigned</span>
            )}
          </div>

          {/* Curriculum capabilities (issue #358) — admins have these implicitly */}
          {item.role !== "school_admin" && item.capabilities.length > 0 && (
            <div className="mt-2 flex flex-wrap items-center gap-1.5">
              {item.capabilities.map((c) => (
                <span
                  key={c}
                  className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700"
                >
                  <BookMarked className="h-3 w-3" />
                  {CAP_LABELS[c] ?? c}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Action buttons */}
        <div className="flex shrink-0 items-center gap-1">
          {isAdmin && item.role !== "school_admin" && (
            <button
              type="button"
              onClick={() => {
                setConfirmPromote(true);
                setActionMsg(null);
              }}
              className="rounded-md p-1.5 text-gray-400 hover:bg-purple-50 hover:text-purple-600"
              aria-label="Promote to school admin"
              title="Promote to admin"
            >
              <Crown className="h-4 w-4" />
            </button>
          )}
          {isAdmin && (
            <button
              type="button"
              onClick={() => {
                setConfirmReset(true);
                setActionMsg(null);
              }}
              className="rounded-md p-1.5 text-gray-400 hover:bg-amber-50 hover:text-amber-600"
              aria-label="Reset password"
              title="Reset password"
            >
              <KeyRound className="h-4 w-4" />
            </button>
          )}
          {isAdmin && item.role !== "school_admin" && (
            <button
              type="button"
              onClick={() => setEditingCaps((v) => !v)}
              className="rounded-md p-1.5 text-gray-400 hover:bg-blue-50 hover:text-blue-600"
              aria-label="Edit curriculum capabilities"
              title="Curriculum capabilities"
            >
              <BookMarked className="h-4 w-4" />
            </button>
          )}
          <button
            type="button"
            onClick={() => setEditing((v) => !v)}
            className="rounded-md p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
            aria-label="Edit grade assignments"
          >
            {editing ? <X className="h-4 w-4" /> : <Pencil className="h-4 w-4" />}
          </button>
        </div>
      </div>

      {/* Reset password confirm */}
      {confirmReset && (
        <div className="mt-3 rounded-lg border border-amber-100 bg-amber-50 p-3 text-sm">
          <p className="text-amber-800">
            Reset <strong>{item.name}</strong>&apos;s password? They will receive a new
            temporary password and must change it on next login.
          </p>
          <div className="mt-2 flex gap-2">
            <Button
              size="sm"
              variant="outline"
              className="border-amber-300 text-amber-700 hover:bg-amber-100"
              onClick={() => doReset()}
              disabled={resetting}
            >
              {resetting ? "Resetting…" : "Yes, reset"}
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setConfirmReset(false)}
              disabled={resetting}
            >
              Cancel
            </Button>
          </div>
        </div>
      )}

      {/* Promote to admin confirm */}
      {confirmPromote && (
        <div className="mt-3 rounded-lg border border-purple-100 bg-purple-50 p-3 text-sm">
          <p className="text-purple-800">
            Promote <strong>{item.name}</strong> to school admin? They will be able to
            manage all teachers and students at this school.
          </p>
          <div className="mt-2 flex gap-2">
            <Button
              size="sm"
              variant="outline"
              className="border-purple-300 text-purple-700 hover:bg-purple-100"
              onClick={() => doPromote()}
              disabled={promoting}
            >
              {promoting ? "Promoting…" : "Yes, promote"}
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setConfirmPromote(false)}
              disabled={promoting}
            >
              Cancel
            </Button>
          </div>
        </div>
      )}

      {/* Temp password reveal */}
      {tempPassword && (
        <div className="mt-3 rounded-lg border border-green-200 bg-green-50 p-3 text-sm">
          <p className="font-medium text-green-800">
            Password reset — share this with {item.name}:
          </p>
          <div className="mt-1.5 flex items-center gap-2">
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
          </div>
          <p className="mt-1.5 text-xs text-green-700">
            They will be required to set a new password on first login.
          </p>
          <button
            type="button"
            onClick={() => setTempPassword(null)}
            className="mt-2 text-xs text-green-600 underline hover:no-underline"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Action result message */}
      {actionMsg && (
        <div className="mt-3 rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-xs text-gray-700">
          {actionMsg}
        </div>
      )}

      {editing && (
        <GradeEditor
          teacherId={item.teacher_id}
          schoolId={schoolId}
          current={item.assigned_grades}
          onDone={() => setEditing(false)}
        />
      )}

      {editingCaps && (
        <CapabilityEditor
          teacherId={item.teacher_id}
          schoolId={schoolId}
          current={item.capabilities}
          onDone={() => setEditingCaps(false)}
        />
      )}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function TeachersPage() {
  const teacher = useTeacher();
  const schoolId = teacher?.school_id ?? "";
  const isAdmin = teacher?.role === "school_admin";

  const { data: teachers, isLoading } = useQuery({
    queryKey: ["teachers", schoolId],
    queryFn: () => listTeachers(schoolId),
    enabled: !!schoolId,
    staleTime: 30_000,
  });

  // Roster summary (#369 VT-2) — total count + grade-wise breakdown, derived
  // client-side from the roster. A teacher assigned to multiple grades counts
  // once per grade; teachers with no grade assigned roll up into "Unassigned".
  const summary = useMemo(() => {
    if (!Array.isArray(teachers)) return null;
    const byGrade = new Map<number, number>();
    let unassigned = 0;
    for (const t of teachers) {
      const grades = t.assigned_grades ?? [];
      if (grades.length === 0) unassigned += 1;
      for (const g of grades) byGrade.set(g, (byGrade.get(g) ?? 0) + 1);
    }
    return {
      total: teachers.length,
      grades: ALL_GRADES.filter((g) => byGrade.has(g)).map((g) => ({
        grade: g,
        count: byGrade.get(g) as number,
      })),
      unassigned,
    };
  }, [teachers]);

  // Provision form state
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [addError, setAddError] = useState<string | null>(null);
  const [addSuccess, setAddSuccess] = useState<string | null>(null);

  const { mutate: doProvision, isPending: provisioning } = useMutation({
    mutationFn: () => provisionTeacher(schoolId, { name, email }),
    onSuccess: (res) => {
      setAddSuccess(res.email);
      setName("");
      setEmail("");
      queryClient.invalidateQueries({ queryKey: ["teachers", schoolId] });
    },
    onError: (err: unknown) => {
      const resp = (
        err as { response?: { status?: number; data?: { detail?: unknown } } }
      )?.response;
      const status = resp?.status;
      if (status === 409) {
        // Prefer the server's explanation — it distinguishes "already on your
        // roster" from "registered at another school" and names the contact
        // route (#572). Falling back only if the API sent nothing usable.
        {
          const serverDetail = (resp?.data as { detail?: unknown } | undefined)?.detail;
          setAddError(
            typeof serverDetail === "string"
              ? serverDetail
              : "That email address is already registered. Try a different address.",
          );
        }
      } else if (status === 422) {
        // FastAPI 422 `detail` is an array of {loc, msg} objects. It must NEVER be
        // set raw — rendering an object array as a React child throws and trips the
        // "This page couldn't load" error boundary (feedback #440). Map it to a
        // field-specific message instead.
        const detail = resp?.data?.detail;
        const fields = Array.isArray(detail)
          ? detail.flatMap((d) =>
              Array.isArray((d as { loc?: unknown[] })?.loc)
                ? ((d as { loc: unknown[] }).loc as unknown[]).map(String)
                : [],
            )
          : [];
        if (fields.includes("email")) {
          setAddError("Enter a valid work email address.");
        } else if (fields.includes("name")) {
          setAddError("Enter the teacher's full name.");
        } else {
          setAddError(
            typeof detail === "string"
              ? detail
              : "Please check the name and email and try again.",
          );
        }
      } else {
        setAddError("Could not add teacher. Please try again.");
      }
    },
  });

  return (
    <div className="max-w-3xl space-y-6 p-6">
      <div className="flex items-center gap-2">
        <GraduationCap className="h-6 w-6 text-indigo-600" />
        <h1 className="text-2xl font-bold text-gray-900">Teacher Management</h1>
      </div>

      {/* ── Roster summary: total + grade-wise breakdown (#369) ── */}
      {summary && summary.total > 0 && (
        <div className="rounded-lg border bg-white p-4 shadow-sm">
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-gray-900 tabular-nums">
              {summary.total}
            </span>
            <span className="text-sm text-gray-500">
              teacher{summary.total !== 1 ? "s" : ""} at this school
            </span>
          </div>
          {(summary.grades.length > 0 || summary.unassigned > 0) && (
            <div className="mt-3 flex flex-wrap gap-1.5">
              {summary.grades.map(({ grade, count }) => (
                <span
                  key={grade}
                  className="inline-flex items-center gap-1.5 rounded-full bg-indigo-50 px-2.5 py-1 text-xs font-medium text-indigo-700"
                >
                  Gr {grade}
                  <span className="rounded-full bg-white px-1.5 text-indigo-800 tabular-nums">
                    {count}
                  </span>
                </span>
              ))}
              {summary.unassigned > 0 && (
                <span className="inline-flex items-center gap-1.5 rounded-full bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-500">
                  Unassigned
                  <span className="rounded-full bg-white px-1.5 text-gray-600 tabular-nums">
                    {summary.unassigned}
                  </span>
                </span>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── Teacher roster ── */}
      <section>
        <h2 className="mb-3 text-sm font-semibold tracking-wide text-gray-500 uppercase">
          Teachers at this school
        </h2>
        {isLoading ? (
          <div className="space-y-3">
            {[1, 2].map((i) => (
              <Skeleton key={i} className="h-20 rounded-lg" />
            ))}
          </div>
        ) : teachers && teachers.length > 0 ? (
          <div className="space-y-3">
            {teachers.map((t) => (
              <TeacherRow
                key={t.teacher_id}
                item={t}
                schoolId={schoolId}
                isAdmin={isAdmin}
              />
            ))}
          </div>
        ) : (
          <p className="text-sm text-gray-400 italic">No teachers found.</p>
        )}
      </section>

      {/* ── Add teacher form (admin only) ── */}
      {isAdmin && (
        <section>
          <Card className="border shadow-sm">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-base">
                <UserPlus className="h-4 w-4 text-indigo-600" />
                Add a teacher
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <Label htmlFor="teacher_name">Full name</Label>
                  <Input
                    id="teacher_name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Jane Smith"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="teacher_email">Work email</Label>
                  <Input
                    id="teacher_email"
                    type="email"
                    value={email}
                    onChange={(e) => {
                      setEmail(e.target.value);
                      setAddError(null);
                    }}
                    placeholder="j.smith@school.edu"
                  />
                </div>
              </div>

              {addError && <p className="text-sm text-red-600">{addError}</p>}
              {addSuccess && (
                <div className="flex items-center gap-2 rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-700">
                  <Check className="h-4 w-4 shrink-0" />
                  Teacher added. A temporary password has been sent to{" "}
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
                disabled={provisioning || !name || !email}
                className="gap-2"
              >
                {provisioning ? "Adding…" : "Add teacher"}
              </Button>
            </CardContent>
          </Card>
        </section>
      )}
    </div>
  );
}
