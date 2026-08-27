"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTeacher } from "@/lib/hooks/useTeacher";
import Link from "next/link";
import {
  listClassrooms,
  createClassroom,
  updateClassroom,
  type ClassroomItem,
} from "@/lib/api/school-admin";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { Skeleton } from "@/components/ui/skeleton";
import { NoGradesNotice } from "@/components/school/ScopeNote";
import { getMyGradeScope } from "@/lib/api/reports";
import {
  DoorOpen,
  Plus,
  ChevronRight,
  Users,
  BookOpen,
  Archive,
  RotateCcw,
} from "lucide-react";

const ALL_GRADES = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12];

// ── Classroom card ─────────────────────────────────────────────────────────────

function ClassroomCard({
  item,
  schoolId,
  isAdmin,
}: {
  item: ClassroomItem;
  schoolId: string;
  isAdmin: boolean;
}) {
  const queryClient = useQueryClient();
  const [confirmArchive, setConfirmArchive] = useState(false);

  const { mutate: toggleStatus, isPending } = useMutation({
    mutationFn: () =>
      updateClassroom(schoolId, item.classroom_id, {
        status: item.status === "active" ? "archived" : "active",
      }),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["classrooms", schoolId] }),
  });

  return (
    <div
      className={`rounded-lg border bg-white p-4 shadow-sm ${
        item.status === "archived" ? "opacity-60" : ""
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="font-medium text-gray-900">{item.name}</span>
            {item.grade && (
              <span className="rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-700">
                Grade {item.grade}
              </span>
            )}
            {item.status === "archived" && (
              <Badge className="border-gray-200 bg-gray-100 text-xs text-gray-500">
                Archived
              </Badge>
            )}
          </div>
          {item.teacher_name && (
            <p className="mt-0.5 text-sm text-gray-500">Lead: {item.teacher_name}</p>
          )}
          <div className="mt-2 flex items-center gap-4 text-xs text-gray-500">
            <span className="flex items-center gap-1">
              <Users className="h-3 w-3" />
              {item.student_count} student{item.student_count !== 1 ? "s" : ""}
            </span>
            <span className="flex items-center gap-1">
              <BookOpen className="h-3 w-3" />
              {item.package_count} package{item.package_count !== 1 ? "s" : ""}
            </span>
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-1">
          {isAdmin && (
            <>
              {!confirmArchive ? (
                <button
                  type="button"
                  onClick={() => setConfirmArchive(true)}
                  className="rounded-md p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
                  aria-label={
                    item.status === "active" ? "Archive classroom" : "Restore classroom"
                  }
                  title={item.status === "active" ? "Archive" : "Restore"}
                >
                  {item.status === "active" ? (
                    <Archive className="h-4 w-4" />
                  ) : (
                    <RotateCcw className="h-4 w-4" />
                  )}
                </button>
              ) : (
                <div className="flex items-center gap-1">
                  <Button
                    size="sm"
                    variant="outline"
                    className="h-7 text-xs"
                    onClick={() => {
                      setConfirmArchive(false);
                      toggleStatus();
                    }}
                    disabled={isPending}
                  >
                    {isPending ? "…" : "Confirm"}
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-7 text-xs"
                    onClick={() => setConfirmArchive(false)}
                  >
                    Cancel
                  </Button>
                </div>
              )}
            </>
          )}
          <Link
            href={`/school/classrooms/${item.classroom_id}`}
            className="flex items-center gap-1 rounded-md px-2 py-1 text-sm font-medium text-indigo-600 hover:bg-indigo-50"
          >
            Manage
            <ChevronRight className="h-4 w-4" />
          </Link>
        </div>
      </div>
    </div>
  );
}

// ── Create form ────────────────────────────────────────────────────────────────

function CreateClassroomForm({ schoolId }: { schoolId: string }) {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [grade, setGrade] = useState<number | "">("");
  const [error, setError] = useState<string | null>(null);

  const { mutate, isPending } = useMutation({
    mutationFn: () =>
      createClassroom(schoolId, {
        name,
        grade: grade === "" ? null : Number(grade),
      }),
    onSuccess: () => {
      setName("");
      setGrade("");
      setError(null);
      queryClient.invalidateQueries({ queryKey: ["classrooms", schoolId] });
    },
    onError: () => setError("Could not create classroom. Please try again."),
  });

  return (
    <Card className="border shadow-sm">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-base">
          <Plus className="h-4 w-4 text-indigo-600" />
          New classroom
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <Label htmlFor="cls_name">Classroom name</Label>
            <Input
              id="cls_name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Grade 8 — Section A"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="cls_grade">Grade (optional)</Label>
            <select
              id="cls_grade"
              value={grade}
              onChange={(e) =>
                setGrade(e.target.value === "" ? "" : Number(e.target.value))
              }
              className="border-input focus-visible:ring-ring flex h-9 w-full rounded-md border bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:ring-1 focus-visible:outline-none"
            >
              <option value="">No specific grade</option>
              {ALL_GRADES.map((g) => (
                <option key={g} value={g}>
                  Grade {g}
                </option>
              ))}
            </select>
          </div>
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <Button
          onClick={() => {
            setError(null);
            mutate();
          }}
          disabled={isPending || !name.trim()}
          className="gap-2"
        >
          {isPending ? "Creating…" : "Create classroom"}
        </Button>
      </CardContent>
    </Card>
  );
}

// ── Page ───────────────────────────────────────────────────────────────────────

type ScopeFilter = "mine" | "all";

export default function ClassroomsPage() {
  const teacher = useTeacher();
  const schoolId = teacher?.school_id ?? "";
  const teacherId = teacher?.teacher_id ?? null;
  const isAdmin = teacher?.role === "school_admin";
  const [gradeFilter, setGradeFilter] = useState<number | "">("");

  // The caller's GRADE scope — distinct from the mine/all filter below.
  // Needed so an empty list can be explained instead of claiming the school
  // has no classrooms when the teacher simply cannot see them (#647).
  const { data: gradeScope } = useQuery({
    queryKey: ["my-grade-scope", schoolId],
    queryFn: () => getMyGradeScope(schoolId),
    enabled: !!schoolId,
    staleTime: 300_000,
  });
  const hasNoGradeScope = gradeScope?.kind === "grades" && gradeScope.grades.length === 0;

  const { data: classrooms, isLoading } = useQuery({
    queryKey: ["classrooms", schoolId],
    queryFn: () => listClassrooms(schoolId),
    enabled: !!schoolId,
    staleTime: 30_000,
  });

  // How many classrooms the logged-in teacher leads. If zero (e.g. a brand-new
  // teacher account that hasn't been assigned anywhere), default to "all" so
  // the page isn't empty on first load.
  const myCount = classrooms?.filter((c) => c.teacher_id === teacherId).length ?? 0;
  const [scope, setScope] = useState<ScopeFilter>("mine");

  // Auto-fallback to "all" when the teacher leads nothing — once we know the
  // counts. Without this, a brand-new teacher would land on an empty Classrooms
  // page even though the school has plenty to show.
  const effectiveScope: ScopeFilter = scope === "mine" && myCount === 0 ? "all" : scope;

  // Only offer grades that actually have at least one classroom — empty grades
  // would just give the dropdown stale clutter.
  const presentGrades = Array.from(
    new Set(
      (classrooms ?? [])
        .map((c) => c.grade)
        .filter((g): g is number => typeof g === "number"),
    ),
  ).sort((a, b) => a - b);

  // Apply scope + grade filters before splitting active/archived.
  // - "mine" → only classrooms where the lead teacher is the logged-in user
  // - grade  → only classrooms at the picked grade (gradeless rows hidden when filtering)
  const filtered =
    classrooms?.filter(
      (c) =>
        (effectiveScope === "all" || c.teacher_id === teacherId) &&
        (gradeFilter === "" || c.grade === gradeFilter),
    ) ?? [];
  const active = filtered.filter((c) => c.status === "active");
  const archived = filtered.filter((c) => c.status === "archived");

  return (
    <div className="max-w-3xl space-y-6 p-6">
      <div className="flex items-center gap-2">
        <DoorOpen className="h-6 w-6 text-indigo-600" />
        <h1 className="text-2xl font-bold text-gray-900">Classrooms</h1>
      </div>

      <p className="text-sm text-gray-500">
        A classroom binds a group of students to one or more curriculum packages. Create a
        classroom, assign packages from the catalog or your custom builds, then enrol
        students.
      </p>

      {/* Scope toggle — default to "my classrooms" so a teacher who leads
          even a single class lands on a focused view. Auto-collapses to
          "All" when the teacher leads nothing (e.g. school_admin browsing). */}
      {(classrooms?.length ?? 0) > 0 && (
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <span className="text-gray-700">Show:</span>
          <div className="inline-flex rounded-md border border-gray-200 bg-gray-50 p-0.5">
            <button
              type="button"
              onClick={() => setScope("mine")}
              disabled={myCount === 0}
              className={cn(
                "rounded px-3 py-1 text-xs font-medium transition-colors",
                effectiveScope === "mine"
                  ? "bg-white text-indigo-700 shadow-sm"
                  : "text-gray-500 hover:text-gray-700",
                myCount === 0 && "cursor-not-allowed opacity-40",
              )}
              title={
                myCount === 0 ? "You aren't the lead of any classrooms yet." : undefined
              }
            >
              My classrooms ({myCount})
            </button>
            <button
              type="button"
              onClick={() => setScope("all")}
              className={cn(
                "rounded px-3 py-1 text-xs font-medium transition-colors",
                effectiveScope === "all"
                  ? "bg-white text-indigo-700 shadow-sm"
                  : "text-gray-500 hover:text-gray-700",
              )}
            >
              All classrooms ({classrooms?.length ?? 0})
            </button>
          </div>
        </div>
      )}

      {/* Grade filter — only lists grades that have at least one classroom
          today, so the dropdown stays tight as the school's roster grows. */}
      {presentGrades.length > 0 && (
        <div className="flex items-center gap-3">
          <label
            htmlFor="classroom_grade_filter"
            className="text-sm font-medium text-gray-700"
          >
            Filter by grade
          </label>
          <select
            id="classroom_grade_filter"
            value={gradeFilter}
            onChange={(e) =>
              setGradeFilter(e.target.value === "" ? "" : Number(e.target.value))
            }
            className="border-input focus-visible:ring-ring h-9 rounded-md border bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:ring-1 focus-visible:outline-none"
          >
            <option value="">All grades</option>
            {presentGrades.map((g) => (
              <option key={g} value={g}>
                Grade {g}
              </option>
            ))}
          </select>
          <span className="text-sm text-gray-400">
            {filtered.length} classroom{filtered.length !== 1 ? "s" : ""}
          </span>
        </div>
      )}

      {/* ── Active classrooms ── */}
      <section>
        <h2 className="mb-3 text-sm font-semibold tracking-wide text-gray-500 uppercase">
          Active classrooms
        </h2>
        {isLoading ? (
          <div className="space-y-3">
            {[1, 2].map((i) => (
              <Skeleton key={i} className="h-20 rounded-lg" />
            ))}
          </div>
        ) : active.length > 0 ? (
          <div className="space-y-3">
            {active.map((c) => (
              <ClassroomCard
                key={c.classroom_id}
                item={c}
                schoolId={schoolId}
                isAdmin={isAdmin}
              />
            ))}
          </div>
        ) : // Same false-claim problem as the alerts page: a teacher with no
        // grade assignments is not looking at a school without classrooms,
        // they are looking at classrooms they cannot see (#647).
        hasNoGradeScope ? (
          <NoGradesNotice scope={gradeScope} />
        ) : (
          <p className="text-sm text-gray-400 italic">No active classrooms yet.</p>
        )}
      </section>

      {/* ── Create form (admin only) ── */}
      {isAdmin && <CreateClassroomForm schoolId={schoolId} />}

      {/* ── Archived classrooms ── */}
      {archived.length > 0 && (
        <section>
          <h2 className="mb-3 text-sm font-semibold tracking-wide text-gray-500 uppercase">
            Archived
          </h2>
          <div className="space-y-3">
            {archived.map((c) => (
              <ClassroomCard
                key={c.classroom_id}
                item={c}
                schoolId={schoolId}
                isAdmin={isAdmin}
              />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
