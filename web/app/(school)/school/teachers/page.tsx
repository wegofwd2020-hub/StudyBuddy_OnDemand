"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTeacher } from "@/lib/hooks/useTeacher";
import {
  listTeachers,
  assignTeacherGrades,
  inviteTeacher,
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
} from "lucide-react";

const ALL_GRADES = [5, 6, 7, 8, 9, 10, 11, 12];

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
      next.has(grade) ? next.delete(grade) : next.add(grade);
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

// ── Teacher row ───────────────────────────────────────────────────────────────

function TeacherRow({
  item,
  schoolId,
}: {
  item: TeacherRosterItem;
  schoolId: string;
}) {
  const [editing, setEditing] = useState(false);

  return (
    <div className="rounded-lg border bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
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
        </div>

        <button
          type="button"
          onClick={() => setEditing((v) => !v)}
          className="flex-shrink-0 rounded-md p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
          aria-label="Edit grade assignments"
        >
          {editing ? <X className="h-4 w-4" /> : <Pencil className="h-4 w-4" />}
        </button>
      </div>

      {editing && (
        <GradeEditor
          teacherId={item.teacher_id}
          schoolId={schoolId}
          current={item.assigned_grades}
          onDone={() => setEditing(false)}
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

  // Invite form state
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [inviteError, setInviteError] = useState<string | null>(null);
  const [inviteSuccess, setInviteSuccess] = useState<string | null>(null);

  const { mutate: doInvite, isPending: inviting } = useMutation({
    mutationFn: () => inviteTeacher(schoolId, name, email),
    onSuccess: (res) => {
      setInviteSuccess(res.email);
      setName("");
      setEmail("");
      queryClient.invalidateQueries({ queryKey: ["teachers", schoolId] });
    },
    onError: (err: unknown) => {
      const detail = (err as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail;
      setInviteError(detail ?? "Invite failed. The email may already be registered.");
    },
  });

  return (
    <div className="max-w-3xl space-y-6 p-6">
      <div className="flex items-center gap-2">
        <GraduationCap className="h-6 w-6 text-indigo-600" />
        <h1 className="text-2xl font-bold text-gray-900">Teacher Management</h1>
      </div>

      {/* ── Teacher roster ── */}
      <section>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500">
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
              <TeacherRow key={t.teacher_id} item={t} schoolId={schoolId} />
            ))}
          </div>
        ) : (
          <p className="text-sm text-gray-400 italic">No teachers found.</p>
        )}
      </section>

      {/* ── Invite form (admin only) ── */}
      {isAdmin && (
        <section>
          <Card className="border shadow-sm">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-base">
                <UserPlus className="h-4 w-4 text-indigo-600" />
                Invite a teacher
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
                      setInviteError(null);
                    }}
                    placeholder="j.smith@school.edu"
                  />
                </div>
              </div>

              {inviteError && <p className="text-sm text-red-600">{inviteError}</p>}
              {inviteSuccess && (
                <div className="flex items-center gap-2 rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-700">
                  <Check className="h-4 w-4 shrink-0" />
                  Invitation sent to{" "}
                  <span className="font-medium">{inviteSuccess}</span>. They will
                  receive an Auth0 login link.
                </div>
              )}

              <Button
                onClick={() => {
                  setInviteError(null);
                  setInviteSuccess(null);
                  doInvite();
                }}
                disabled={inviting || !name || !email}
                className="gap-2"
              >
                {inviting ? "Sending…" : "Send invitation"}
              </Button>
            </CardContent>
          </Card>
        </section>
      )}
    </div>
  );
}
