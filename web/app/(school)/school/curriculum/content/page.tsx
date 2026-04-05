"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { useTeacher } from "@/lib/hooks/useTeacher";
import {
  listSchoolContentSubjects,
  listTeachers,
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

export default function SchoolContentPage() {
  const teacher = useTeacher();
  const schoolId = teacher?.school_id ?? "";
  const isAdmin = teacher?.role === "school_admin";

  // Get this teacher's assigned grades (to default the grade filter)
  const { data: teachers } = useQuery({
    queryKey: ["teachers", schoolId],
    queryFn: () => listTeachers(schoolId),
    enabled: !!schoolId && !isAdmin,
    staleTime: 30_000,
  });

  const assignedGrades = useMemo(() => {
    if (isAdmin || !teachers || !teacher?.teacher_id) return null;
    const me = teachers.find((t) => t.teacher_id === teacher.teacher_id);
    return me?.assigned_grades ?? [];
  }, [teachers, teacher, isAdmin]);

  const [gradeFilter, setGradeFilter] = useState<number | "all">("all");

  const { data: subjects, isLoading } = useQuery({
    queryKey: ["school-content-subjects", schoolId],
    queryFn: () => listSchoolContentSubjects(schoolId),
    enabled: !!schoolId,
    staleTime: 60_000,
  });

  // Filter: admins see all, teachers see only their assigned grades (with override via UI)
  const visibleSubjects = useMemo(() => {
    if (!subjects) return [];
    let list = subjects;
    if (!isAdmin && assignedGrades && assignedGrades.length > 0) {
      list = list.filter((s) => assignedGrades.includes(s.grade));
    }
    if (gradeFilter !== "all") {
      list = list.filter((s) => s.grade === gradeFilter);
    }
    return list;
  }, [subjects, isAdmin, assignedGrades, gradeFilter]);

  // Available grades for the filter pill row
  const availableGrades = useMemo(() => {
    if (!subjects) return [];
    const base = isAdmin ? subjects : subjects.filter((s) =>
      assignedGrades ? assignedGrades.includes(s.grade) : true,
    );
    return [...new Set(base.map((s) => s.grade))].sort((a, b) => a - b);
  }, [subjects, isAdmin, assignedGrades]);

  // Group by grade for display
  const grouped = useMemo(() => {
    const map = new Map<number, typeof visibleSubjects>();
    for (const s of visibleSubjects) {
      const list = map.get(s.grade) ?? [];
      list.push(s);
      map.set(s.grade, list);
    }
    return [...map.entries()].sort((a, b) => a[0] - b[0]);
  }, [visibleSubjects]);

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

      {/* Grade filter pills */}
      {availableGrades.length > 1 && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-medium text-gray-500">Filter:</span>
          <button
            onClick={() => setGradeFilter("all")}
            className={cn(
              "rounded-full px-3 py-1 text-xs font-medium transition-colors",
              gradeFilter === "all"
                ? "bg-indigo-600 text-white"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200",
            )}
          >
            All grades
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

      {isLoading ? (
        <div className="space-y-4">
          {[1, 2].map((i) => (
            <Skeleton key={i} className="h-36 rounded-lg" />
          ))}
        </div>
      ) : grouped.length === 0 ? (
        <div className="rounded-lg border border-gray-200 bg-white p-8 text-center">
          <FileText className="mx-auto mb-3 h-10 w-10 text-gray-300" />
          <p className="text-sm font-medium text-gray-500">No curriculum content found.</p>
          <p className="mt-1 text-xs text-gray-400">
            {!isAdmin && assignedGrades?.length === 0
              ? "You have no grades assigned yet. Ask your school admin to assign grades."
              : "Upload a curriculum and trigger the pipeline to generate content."}
          </p>
        </div>
      ) : (
        grouped.map(([grade, items]) => (
          <section key={grade}>
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500">
              Grade {grade}
            </h2>
            <div className="space-y-2">
              {items.map((item) => (
                <SubjectRow key={item.version_id} item={item} />
              ))}
            </div>
          </section>
        ))
      )}
    </div>
  );
}

function SubjectRow({ item }: { item: SchoolContentSubject }) {
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
          {!item.has_content && (
            <span className="text-xs text-gray-400 italic">No files yet</span>
          )}
        </div>
        <p className="mt-0.5 text-xs text-gray-500">
          v{item.version_number} · {item.unit_count} unit{item.unit_count !== 1 ? "s" : ""} ·{" "}
          Generated {new Date(item.generated_at).toLocaleDateString()}
        </p>
      </div>
      <ChevronRight className="ml-3 h-4 w-4 shrink-0 text-gray-400" />
    </Link>
  );
}
