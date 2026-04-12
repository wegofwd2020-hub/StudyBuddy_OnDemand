"use client";

/**
 * SetupChecklist — Layer 1.5 onboarding banner for new school admins.
 *
 * Shown on the school dashboard when setup_complete=false.
 * Auto-disappears once all four required steps are done.
 * Each item links directly to the relevant management page.
 */

import Link from "next/link";
import { CheckCircle2, Circle, ChevronRight, X } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { getSetupStatus, type SetupStatus } from "@/lib/api/school-admin";

interface ChecklistItem {
  label: string;
  description: string;
  href: string;
  done: (s: SetupStatus) => boolean;
}

const STEPS: ChecklistItem[] = [
  {
    label: "Add a teacher",
    description: "Provision at least one teacher to your school.",
    href: "/school/teachers",
    done: (s) => s.teacher_count > 0,
  },
  {
    label: "Enrol a student",
    description: "Add students so teachers can track their progress.",
    href: "/school/students",
    done: (s) => s.student_count > 0,
  },
  {
    label: "Create a classroom",
    description: "Group students into a classroom to assign content.",
    href: "/school/classrooms",
    done: (s) => s.classroom_count > 0,
  },
  {
    label: "Assign a curriculum",
    description: "Browse the catalog or build a custom curriculum, then assign it to a classroom.",
    href: "/school/catalog",
    done: (s) => s.curriculum_assigned,
  },
];

export function SetupChecklist({ schoolId }: { schoolId: string }) {
  const [dismissed, setDismissed] = useState(false);

  const { data: status, isLoading } = useQuery({
    queryKey: ["setup-status", schoolId],
    queryFn: () => getSetupStatus(schoolId),
    enabled: !!schoolId && !dismissed,
    staleTime: 30_000,
  });

  // Hide while loading, after dismiss, or once fully complete
  if (isLoading || dismissed || !status || status.setup_complete) return null;

  const completedCount = STEPS.filter((step) => step.done(status)).length;

  return (
    <div className="rounded-xl border border-violet-200 bg-violet-50 p-5 shadow-sm">
      {/* Header */}
      <div className="mb-4 flex items-start justify-between gap-4">
        <div>
          <h2 className="text-base font-semibold text-violet-900">
            Set up your school
          </h2>
          <p className="mt-0.5 text-sm text-violet-700">
            Complete these steps to get your school ready for students.{" "}
            <span className="font-medium">
              {completedCount} of {STEPS.length} done.
            </span>
          </p>
        </div>
        <button
          onClick={() => setDismissed(true)}
          aria-label="Dismiss setup checklist"
          className="mt-0.5 rounded-md p-1 text-violet-400 hover:bg-violet-100 hover:text-violet-600"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Progress bar */}
      <div className="mb-4 h-1.5 w-full overflow-hidden rounded-full bg-violet-200">
        <div
          className="h-full rounded-full bg-violet-600 transition-all duration-500"
          style={{ width: `${(completedCount / STEPS.length) * 100}%` }}
        />
      </div>

      {/* Steps */}
      <ol className="space-y-2">
        {STEPS.map((step) => {
          const done = step.done(status);
          return (
            <li key={step.href}>
              {done ? (
                <div className="flex items-start gap-3 rounded-lg px-3 py-2.5">
                  <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-green-500" />
                  <div>
                    <p className="text-sm font-medium text-gray-500 line-through">
                      {step.label}
                    </p>
                  </div>
                </div>
              ) : (
                <Link
                  href={step.href}
                  className="group flex items-start gap-3 rounded-lg px-3 py-2.5 hover:bg-violet-100"
                >
                  <Circle className="mt-0.5 h-5 w-5 shrink-0 text-violet-300 group-hover:text-violet-500" />
                  <div className="flex-1">
                    <p className="text-sm font-medium text-violet-900">
                      {step.label}
                    </p>
                    <p className="text-xs text-violet-600">{step.description}</p>
                  </div>
                  <ChevronRight className="mt-0.5 h-4 w-4 shrink-0 text-violet-300 group-hover:text-violet-500" />
                </Link>
              )}
            </li>
          );
        })}
      </ol>
    </div>
  );
}
