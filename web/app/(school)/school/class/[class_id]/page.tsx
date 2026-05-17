"use client";

import { useState } from "react";
import { useQuery, useQueries } from "@tanstack/react-query";
import { useTeacher } from "@/lib/hooks/useTeacher";
import { getClassMetrics, type ClassStudentRow } from "@/lib/api/reports";
import { listClassrooms, getClassroom } from "@/lib/api/school-admin";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { LinkButton } from "@/components/ui/link-button";
import { ArrowUpDown, ChevronUp, ChevronDown, Users } from "lucide-react";
import { cn } from "@/lib/utils";

type ScopeFilter = "mine" | "all";

type SortKey = keyof Pick<
  ClassStudentRow,
  "student_name" | "grade" | "units_completed" | "avg_score_pct" | "last_active"
>;
type SortDir = "asc" | "desc";

function sortRows(
  rows: ClassStudentRow[],
  key: SortKey,
  dir: SortDir,
): ClassStudentRow[] {
  return [...rows].sort((a, b) => {
    const av = a[key];
    const bv = b[key];
    if (av === null || av === undefined) return 1;
    if (bv === null || bv === undefined) return -1;
    const cmp = av < bv ? -1 : av > bv ? 1 : 0;
    return dir === "asc" ? cmp : -cmp;
  });
}

function ScoreBar({ pct }: { pct: number }) {
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-gray-100">
        <div
          className={cn(
            "h-full rounded-full",
            pct >= 70 ? "bg-green-500" : pct >= 50 ? "bg-yellow-400" : "bg-red-400",
          )}
          style={{ width: `${Math.min(pct, 100)}%` }}
        />
      </div>
      <span className="w-8 text-right text-xs text-gray-600">{pct.toFixed(0)}%</span>
    </div>
  );
}

export default function ClassOverviewPage() {
  const teacher = useTeacher();
  const schoolId = teacher?.school_id ?? "";
  const teacherId = teacher?.teacher_id ?? null;
  const [sortKey, setSortKey] = useState<SortKey>("student_name");
  const [sortDir, setSortDir] = useState<SortDir>("asc");
  const [gradeFilter, setGradeFilter] = useState<number | undefined>();
  const [scope, setScope] = useState<ScopeFilter>("mine");

  // School-wide metrics drives the table rows. Grade filtering is done
  // server-side; scope (mine/all) is applied client-side after we know which
  // students belong to the logged-in teacher's classrooms.
  const { data, isLoading } = useQuery({
    queryKey: ["class-metrics", schoolId, gradeFilter],
    queryFn: () => getClassMetrics(schoolId, gradeFilter),
    enabled: !!schoolId,
    staleTime: 120_000,
  });

  // Which classrooms does the logged-in teacher lead? "My students" needs
  // this to know which students to keep.
  const { data: classrooms } = useQuery({
    queryKey: ["classrooms", schoolId],
    queryFn: () => listClassrooms(schoolId),
    enabled: !!schoolId,
    staleTime: 60_000,
  });
  const myClassrooms = (classrooms ?? []).filter((c) => c.teacher_id === teacherId);

  // Pull the per-classroom roster for each of my classrooms in parallel.
  // listClassrooms only returns counts; getClassroom returns the full
  // students array we need to compute "my student_ids".
  const myClassroomDetails = useQueries({
    queries: myClassrooms.map((c) => ({
      queryKey: ["classroom-detail", schoolId, c.classroom_id],
      queryFn: () => getClassroom(schoolId, c.classroom_id),
      enabled: !!schoolId,
      staleTime: 60_000,
    })),
  });

  const myStudentIds = new Set<string>();
  for (const q of myClassroomDetails) {
    for (const s of q.data?.students ?? []) {
      myStudentIds.add(s.student_id);
    }
  }
  const myCount = myStudentIds.size;

  // Auto-fallback to "all" if the teacher leads no classrooms with students
  // (e.g. a school_admin browsing the school overview).
  const effectiveScope: ScopeFilter = scope === "mine" && myCount === 0 ? "all" : scope;

  function toggleSort(key: SortKey) {
    if (sortKey === key) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else {
      setSortKey(key);
      setSortDir("asc");
    }
  }

  const SortIcon = ({ k }: { k: SortKey }) => {
    if (sortKey !== k) return <ArrowUpDown className="h-3 w-3 text-gray-300" />;
    return sortDir === "asc" ? (
      <ChevronUp className="h-3 w-3 text-blue-500" />
    ) : (
      <ChevronDown className="h-3 w-3 text-blue-500" />
    );
  };

  // Apply scope filter to the server-fetched student list.
  const scopedStudents =
    effectiveScope === "all"
      ? (data?.students ?? [])
      : (data?.students ?? []).filter((s) => myStudentIds.has(s.student_id));

  const rows = sortRows(scopedStudents, sortKey, sortDir);

  // Grade pills should only show grades that have at least one student in the
  // current scope — keeps the rail tight when the teacher only has Grade 11
  // students, for example.
  const presentGrades = Array.from(
    new Set(
      (data?.students ?? [])
        .filter((s) => effectiveScope === "all" || myStudentIds.has(s.student_id))
        .map((s) => s.grade),
    ),
  ).sort((a, b) => a - b);

  return (
    <div className="max-w-5xl space-y-6 p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold text-gray-900">Class Overview</h1>
        <div className="flex flex-wrap items-center gap-3">
          {/* Scope toggle — default to "my students" so the page is focused for
              teachers who lead classrooms. Disabled / hidden when the user
              leads no rosters (e.g. school_admin viewing all). */}
          {(classrooms?.length ?? 0) > 0 && (
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
                    ? "You don't have any students in classrooms you lead."
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
                All school ({data?.students.length ?? 0})
              </button>
            </div>
          )}

          {presentGrades.length > 0 && (
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-500">Grade:</span>
              <div className="flex gap-1">
                <button
                  onClick={() => setGradeFilter(undefined)}
                  className={cn(
                    "rounded px-2 py-1 text-xs font-medium transition-colors",
                    gradeFilter === undefined
                      ? "bg-blue-600 text-white"
                      : "border bg-white text-gray-500 hover:text-gray-900",
                  )}
                >
                  All
                </button>
                {presentGrades.map((g) => (
                  <button
                    key={g}
                    onClick={() => setGradeFilter(g)}
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
            </div>
          )}
        </div>
      </div>
      <Card className="border shadow-sm">
        <CardHeader className="pb-2">
          <CardTitle className="text-base">
            {isLoading
              ? "Loading…"
              : `${rows.length} student${rows.length !== 1 ? "s" : ""}`}
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="space-y-2 p-4">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-10 rounded" />
              ))}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-gray-50">
                    {(
                      [
                        ["student_name", "Student"],
                        ["grade", "Grade"],
                        ["units_completed", "Units done"],
                        ["avg_score_pct", "Avg score"],
                        ["last_active", "Last active"],
                      ] as [SortKey, string][]
                    ).map(([key, label]) => (
                      <th
                        key={key}
                        className="cursor-pointer px-4 py-2.5 text-left text-xs font-medium whitespace-nowrap text-gray-500 select-none"
                        onClick={() => toggleSort(key)}
                      >
                        <span className="flex items-center gap-1">
                          {label}
                          <SortIcon k={key} />
                        </span>
                      </th>
                    ))}
                    <th className="px-4 py-2.5" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {rows.map((row) => (
                    <tr
                      key={row.student_id}
                      className="transition-colors hover:bg-gray-50"
                    >
                      <td className="px-4 py-3 font-medium text-gray-900">
                        {row.student_name}
                      </td>
                      <td className="px-4 py-3 text-gray-500">G{row.grade}</td>
                      <td className="px-4 py-3 text-gray-600">
                        {row.units_completed}
                        <span className="text-gray-400">/{row.total_units}</span>
                      </td>
                      <td className="min-w-[120px] px-4 py-3">
                        <ScoreBar pct={row.avg_score_pct} />
                      </td>
                      <td className="px-4 py-3 text-xs text-gray-400">
                        {row.last_active
                          ? new Date(row.last_active).toLocaleDateString()
                          : "Never"}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <LinkButton
                          href={`/school/student/${row.student_id}`}
                          variant="outline"
                          size="sm"
                          className="h-7 text-xs"
                        >
                          Detail
                        </LinkButton>
                      </td>
                    </tr>
                  ))}
                  {rows.length === 0 && (
                    <tr>
                      <td colSpan={6} className="px-4 py-12 text-center">
                        <Users className="mx-auto mb-2 h-8 w-8 text-gray-300" />
                        <p className="text-sm font-medium text-gray-500">
                          No students enrolled yet
                        </p>
                        <p className="mt-0.5 text-xs text-gray-400">
                          Upload a roster or enrol students via the school portal.
                        </p>
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
