"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { useTeacher } from "@/lib/hooks/useTeacher";
import {
  listTeachers,
  getRoster,
  getLibrary,
  listClassrooms,
} from "@/lib/api/school-admin";
import {
  computeSetupChecklist,
  nextIncompleteIndex,
  type SetupSignals,
} from "@/lib/school/setup-checklist";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { CheckCircle2, Circle, ArrowRight, Rocket } from "lucide-react";
import { cn } from "@/lib/utils";

export default function SchoolSetupPage() {
  const teacher = useTeacher();
  const schoolId = teacher?.school_id ?? "";
  const enabled = !!schoolId;

  const teachersQ = useQuery({
    queryKey: ["teachers", schoolId],
    queryFn: () => listTeachers(schoolId),
    enabled,
  });
  const rosterQ = useQuery({
    queryKey: ["roster", schoolId],
    queryFn: () => getRoster(schoolId),
    enabled,
  });
  const libraryQ = useQuery({
    queryKey: ["library", schoolId],
    queryFn: () => getLibrary(schoolId),
    enabled,
  });
  const classroomsQ = useQuery({
    queryKey: ["classrooms", schoolId],
    queryFn: () => listClassrooms(schoolId),
    enabled,
  });

  const loading =
    teachersQ.isLoading ||
    rosterQ.isLoading ||
    libraryQ.isLoading ||
    classroomsQ.isLoading;

  if (loading) {
    return (
      <div className="max-w-2xl space-y-4 p-6">
        <Skeleton className="h-8 w-64" />
        {[0, 1, 2, 3, 4, 5].map((i) => (
          <Skeleton key={i} className="h-20 rounded-lg" />
        ))}
      </div>
    );
  }

  const classrooms = classroomsQ.data ?? [];
  const signals: SetupSignals = {
    teacherCount: (teachersQ.data ?? []).length,
    studentCount: (rosterQ.data?.roster ?? []).length,
    activeAdoptionCount: (libraryQ.data?.adoptions ?? []).filter(
      (a) => a.status === "active",
    ).length,
    classroomCount: classrooms.length,
    classroomsWithPackage: classrooms.filter((c) => c.package_count > 0).length,
    classroomsWithStudent: classrooms.filter((c) => c.student_count > 0).length,
  };

  const steps = computeSetupChecklist(signals);
  const nextIdx = nextIncompleteIndex(steps);
  const doneCount = steps.filter((s) => s.done).length;
  const allDone = nextIdx === -1;

  return (
    <div className="max-w-2xl space-y-6 p-6">
      <header className="flex items-start gap-3">
        <Rocket className="mt-0.5 h-6 w-6 shrink-0 text-indigo-600" aria-hidden />
        <div>
          <h1 className="text-xl font-bold text-gray-900">Set up your school</h1>
          <p className="mt-1 text-sm text-gray-500">
            Follow these steps to go from an empty school to students seeing lessons. We
            tick each one off automatically as you complete it.
          </p>
        </div>
      </header>

      {/* Progress */}
      <div className="rounded-lg border border-gray-100 bg-white p-4">
        <div className="mb-2 flex items-center justify-between text-sm">
          <span className="font-medium text-gray-700">
            {allDone ? "All set 🎉" : `Step ${doneCount + 1} of ${steps.length}`}
          </span>
          <span className="text-gray-400">
            {doneCount}/{steps.length} done
          </span>
        </div>
        <div className="h-2 w-full overflow-hidden rounded-full bg-gray-100">
          <div
            className="h-full rounded-full bg-indigo-600 transition-all"
            style={{ width: `${(doneCount / steps.length) * 100}%` }}
          />
        </div>
      </div>

      {/* Steps */}
      <ol className="space-y-3">
        {steps.map((step, i) => {
          const isNext = i === nextIdx;
          return (
            <li
              key={step.key}
              className={cn(
                "flex items-start gap-3 rounded-lg border p-4 transition-colors",
                step.done
                  ? "border-gray-100 bg-white"
                  : isNext
                    ? "border-indigo-300 bg-indigo-50 shadow-sm"
                    : "border-gray-100 bg-white opacity-70",
              )}
            >
              {step.done ? (
                <CheckCircle2
                  className="mt-0.5 h-5 w-5 shrink-0 text-green-600"
                  aria-hidden
                />
              ) : (
                <Circle
                  className={cn(
                    "mt-0.5 h-5 w-5 shrink-0",
                    isNext ? "text-indigo-600" : "text-gray-300",
                  )}
                  aria-hidden
                />
              )}
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-medium text-gray-400">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <p
                    className={cn(
                      "font-medium",
                      step.done ? "text-gray-500 line-through" : "text-gray-900",
                    )}
                  >
                    {step.title}
                  </p>
                  {isNext && (
                    <span className="rounded-full bg-indigo-600 px-2 py-0.5 text-xs font-medium text-white">
                      Next
                    </span>
                  )}
                </div>
                <p className="mt-1 text-sm text-gray-500">{step.description}</p>
              </div>
              <Link href={step.href} className="shrink-0 self-center">
                <Button
                  size="sm"
                  variant={isNext ? "default" : "outline"}
                  className="gap-1"
                >
                  {step.done ? "Review" : "Go"}
                  <ArrowRight className="h-3.5 w-3.5" aria-hidden />
                </Button>
              </Link>
            </li>
          );
        })}
      </ol>

      {allDone && (
        <div className="rounded-lg border border-green-200 bg-green-50 p-4 text-sm text-green-800">
          Your school is set up. Students enrolled in a class with an assigned curriculum
          can log in and start learning.
        </div>
      )}
    </div>
  );
}
