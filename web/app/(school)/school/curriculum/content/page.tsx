"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useQuery, useQueries } from "@tanstack/react-query";
import { useTeacher } from "@/lib/hooks/useTeacher";
import {
  listSchoolContentSubjects,
  listClassrooms,
  getClassroom,
  type SchoolContentSubject,
} from "@/lib/api/school-admin";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { BookOpen, ChevronRight, FileText } from "lucide-react";
import { cn } from "@/lib/utils";

const STATUS_STYLE: Record<string, string> = {
  approved: "bg-green-50 text-green-700 border-green-200",
  published: "bg-blue-50 text-blue-700 border-blue-100",
  in_review: "bg-yellow-50 text-yellow-700 border-yellow-100",
  pending: "bg-gray-100 text-gray-500 border-gray-200",
  ready_for_review: "bg-orange-50 text-orange-700 border-orange-200",
  rejected: "bg-red-50 text-red-700 border-red-200",
};

function statusLabel(status: string): string {
  if (status === "ready_for_review") return "Ready";
  return status.charAt(0).toUpperCase() + status.slice(1).replace(/_/g, " ");
}

type ScopeFilter = "mine" | "all";

export default function SchoolContentPage() {
  const teacher = useTeacher();
  const schoolId = teacher?.school_id ?? "";
  const teacherId = teacher?.teacher_id ?? null;

  const [gradeFilter, setGradeFilter] = useState<number | "all">("all");
  const [scope, setScope] = useState<ScopeFilter>("mine");

  const { data: subjects, isLoading } = useQuery({
    queryKey: ["school-content-subjects", schoolId],
    queryFn: () => listSchoolContentSubjects(schoolId),
    enabled: !!schoolId,
    staleTime: 60_000,
  });

  // Look up the logged-in teacher's classrooms so we can scope "My content"
  // to the curricula those classrooms have adopted.
  const { data: classrooms } = useQuery({
    queryKey: ["classrooms", schoolId],
    queryFn: () => listClassrooms(schoolId),
    enabled: !!schoolId,
    staleTime: 60_000,
  });
  const myClassrooms = (classrooms ?? []).filter(
    (c) => c.teacher_id === teacherId,
  );

  // Pull full classroom details in parallel so we can read each one's package
  // list. listClassrooms only returns counts; getClassroom returns packages.
  const myClassroomDetails = useQueries({
    queries: myClassrooms.map((c) => ({
      queryKey: ["classroom-detail", schoolId, c.classroom_id],
      queryFn: () => getClassroom(schoolId, c.classroom_id),
      enabled: !!schoolId,
      staleTime: 60_000,
    })),
  });

  const myCurriculaIds = useMemo(() => {
    const ids = new Set<string>();
    for (const q of myClassroomDetails) {
      for (const p of q.data?.packages ?? []) {
        ids.add(p.curriculum_id);
      }
    }
    return ids;
  }, [myClassroomDetails]);

  // Roll multiple versions of the same subject up to a single row. Pick the
  // highest version_number as the "current" version, count the rest as
  // history. Without this, Grade 11 Chemistry v1..v4 shows up as four rows
  // and clutters the library page.
  const rollupKey = (s: SchoolContentSubject) =>
    `${s.curriculum_id}::${s.subject}`;

  const rolledSubjects = useMemo(() => {
    if (!subjects) return [];
    const byKey = new Map<
      string,
      { latest: SchoolContentSubject; versionCount: number }
    >();
    for (const s of subjects) {
      const k = rollupKey(s);
      const existing = byKey.get(k);
      if (!existing) {
        byKey.set(k, { latest: s, versionCount: 1 });
      } else {
        existing.versionCount += 1;
        if (s.version_number > existing.latest.version_number) {
          existing.latest = s;
        }
      }
    }
    return [...byKey.values()];
  }, [subjects]);

  // "My content" count drives the auto-fallback when the teacher leads
  // nothing (e.g. school_admin browsing the school's full library). Count
  // rolled-up topics, not raw version rows.
  const myCount = useMemo(
    () =>
      rolledSubjects.filter((r) => myCurriculaIds.has(r.latest.curriculum_id))
        .length,
    [rolledSubjects, myCurriculaIds],
  );

  const effectiveScope: ScopeFilter =
    scope === "mine" && myCount === 0 ? "all" : scope;

  // Apply scope first, then grade — narrows the rolled-up topic list step by step.
  const visibleRolledSubjects = useMemo(() => {
    let list = rolledSubjects;
    if (effectiveScope === "mine") {
      list = list.filter((r) => myCurriculaIds.has(r.latest.curriculum_id));
    }
    if (gradeFilter !== "all") {
      list = list.filter((r) => r.latest.grade === gradeFilter);
    }
    return list;
  }, [rolledSubjects, effectiveScope, myCurriculaIds, gradeFilter]);

  // Grade pills derived from the current scope, not all topics — keeps the
  // filter rail focused as the visible set narrows.
  const availableGrades = useMemo(() => {
    const base =
      effectiveScope === "mine"
        ? rolledSubjects.filter((r) =>
            myCurriculaIds.has(r.latest.curriculum_id),
          )
        : rolledSubjects;
    return [...new Set(base.map((r) => r.latest.grade))].sort((a, b) => a - b);
  }, [rolledSubjects, effectiveScope, myCurriculaIds]);

  const totalCount = rolledSubjects.length;

  // Group rolled-up topics by grade for display.
  const grouped = useMemo(() => {
    const map = new Map<number, typeof visibleRolledSubjects>();
    for (const r of visibleRolledSubjects) {
      const list = map.get(r.latest.grade) ?? [];
      list.push(r);
      map.set(r.latest.grade, list);
    }
    return [...map.entries()].sort((a, b) => a[0] - b[0]);
  }, [visibleRolledSubjects]);

  return (
    <div className="max-w-4xl space-y-6 p-6">
      <div className="flex items-center gap-2">
        <BookOpen className="h-6 w-6 text-indigo-600" />
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Curriculum Content</h1>
          <p className="text-sm text-gray-500">
            Browse and review AI-generated lessons, quizzes, tutorials, and experiments.
          </p>
        </div>
      </div>

      {/* Scope toggle + grade filter row */}
      {totalCount > 0 && (
        <div className="flex flex-wrap items-center gap-3">
          {/* Scope toggle — defaults to "my content" (curricula adopted by
              classrooms the user leads). Auto-collapses to "All" if the user
              leads no relevant classrooms. */}
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
                  ? "Your classrooms haven't adopted any content packages yet."
                  : undefined
              }
            >
              My content ({myCount})
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
              All school ({totalCount})
            </button>
          </div>

          {availableGrades.length > 1 && (
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-medium text-gray-500">Grade:</span>
              <button
                onClick={() => setGradeFilter("all")}
                className={cn(
                  "rounded-full px-3 py-1 text-xs font-medium transition-colors",
                  gradeFilter === "all"
                    ? "bg-indigo-600 text-white"
                    : "bg-gray-100 text-gray-600 hover:bg-gray-200",
                )}
              >
                All
              </button>
              {availableGrades.map((g) => (
                <button
                  key={g}
                  onClick={() => setGradeFilter(g === gradeFilter ? "all" : g)}
                  className={cn(
                    "rounded-full px-3 py-1 text-xs font-medium transition-colors",
                    gradeFilter === g
                      ? "bg-indigo-600 text-white"
                      : "bg-gray-100 text-gray-600 hover:bg-gray-200",
                  )}
                >
                  Grade {g}
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {isLoading ? (
        <div className="space-y-4">
          {[1, 2].map((i) => (
            <Skeleton key={i} className="h-36 rounded-lg" />
          ))}
        </div>
      ) : grouped.length === 0 ? (
        <div className="rounded-lg border border-gray-200 bg-white p-8 text-center">
          <FileText className="mx-auto mb-3 h-10 w-10 text-gray-300" />
          <p className="text-sm font-medium text-gray-500">
            No curriculum content found.
          </p>
          <p className="mt-1 text-xs text-gray-400">
            {effectiveScope === "mine"
              ? "Your classrooms haven't adopted any content packages yet. Switch to \"All school\" to browse what's available."
              : "Upload a curriculum and trigger the pipeline to generate content."}
          </p>
        </div>
      ) : (
        grouped.map(([grade, items]) => (
          <section key={grade}>
            <h2 className="mb-3 text-sm font-semibold tracking-wide text-gray-500 uppercase">
              Grade {grade}
            </h2>
            <div className="space-y-2">
              {items.map((rolled) => (
                <SubjectRow
                  key={rollupKey(rolled.latest)}
                  item={rolled.latest}
                  versionCount={rolled.versionCount}
                />
              ))}
            </div>
          </section>
        ))
      )}
    </div>
  );
}

function SubjectRow({
  item,
  versionCount,
}: {
  item: SchoolContentSubject;
  versionCount: number;
}) {
  return (
    <Link
      href={`/school/curriculum/content/${item.version_id}`}
      className={cn(
        "flex items-center justify-between rounded-lg border bg-white p-4 shadow-sm transition-colors hover:bg-indigo-50",
        !item.has_content && "opacity-60",
      )}
    >
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="font-medium text-gray-900">
            {item.subject_name ?? item.subject}
          </span>
          <Badge
            className={cn(
              "text-xs",
              STATUS_STYLE[item.status] ?? "bg-gray-100 text-gray-500",
            )}
          >
            {statusLabel(item.status)}
          </Badge>
          {versionCount > 1 && (
            <span
              className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-500"
              title={`${versionCount} versions of this subject — click to open the latest (v${item.version_number}).`}
            >
              {versionCount} versions
            </span>
          )}
          {!item.has_content && (
            <span className="text-xs text-gray-400 italic">No files yet</span>
          )}
        </div>
        <p className="mt-0.5 text-xs text-gray-500">
          Latest v{item.version_number} · {item.unit_count} unit
          {item.unit_count !== 1 ? "s" : ""} · Generated{" "}
          {new Date(item.generated_at).toLocaleDateString()}
        </p>
      </div>
      <ChevronRight className="ml-3 h-4 w-4 shrink-0 text-gray-400" />
    </Link>
  );
}
