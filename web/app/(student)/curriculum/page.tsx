"use client";

import { useCurriculumTree } from "@/lib/hooks/useCurriculumTree";
import { useProgressHistory } from "@/lib/hooks/useProgress";
import { LinkButton } from "@/components/ui/link-button";
import { Skeleton } from "@/components/ui/skeleton";
import { OfflineBanner } from "@/components/student/OfflineBanner";
import { useTranslations } from "next-intl";
import { FlaskConical, CheckCircle2, Circle, AlertCircle, Clock, BookOpen } from "lucide-react";
import { cn } from "@/lib/utils";
import type { UnitStatus } from "@/lib/types/api";

const STATUS_CONFIG: Record<
  UnitStatus,
  { icon: typeof Circle; color: string; label: string }
> = {
  completed: { icon: CheckCircle2, color: "text-green-500", label: "Completed" },
  needs_retry: { icon: AlertCircle, color: "text-amber-500", label: "Needs retry" },
  in_progress: { icon: Clock, color: "text-blue-500", label: "In progress" },
  not_started: { icon: Circle, color: "text-gray-300", label: "Not started" },
};

export default function CurriculumMapPage() {
  const t = useTranslations("curriculum_map_screen");
  const { data: tree, isLoading: treeLoading } = useCurriculumTree();
  const { data: history, isLoading: histLoading } = useProgressHistory(100);

  const loading = treeLoading || histLoading;

  // Build status map from progress history
  const statusMap = new Map<string, UnitStatus>();
  history?.unit_progress?.forEach((up) => statusMap.set(up.unit_id, up.status));

  return (
    <div className="flex flex-col">
      <OfflineBanner />
      <div className="max-w-5xl space-y-8 p-6">
        <h1 className="text-2xl font-bold text-gray-900">{t("title")}</h1>

        {/* Legend */}
        <div className="flex flex-wrap gap-4 text-xs text-gray-500">
          {Object.entries(STATUS_CONFIG).map(([status, { icon: Icon, color, label }]) => (
            <span key={status} className="flex items-center gap-1.5">
              <Icon className={cn("h-3.5 w-3.5", color)} />
              {label}
            </span>
          ))}
        </div>

        {loading ? (
          <div className="space-y-6">
            {[...Array(3)].map((_, i) => (
              <Skeleton key={i} className="h-32 rounded-lg" />
            ))}
          </div>
        ) : !tree?.subjects.length ? (
          <div className="rounded-xl border border-gray-200 bg-white py-16 text-center">
            <BookOpen className="mx-auto mb-3 h-10 w-10 text-gray-300" />
            <p className="mb-1 text-sm font-medium text-gray-600">
              {t("no_units")}
            </p>
            <p className="text-xs text-gray-400">
              Your curriculum hasn&apos;t been published yet. Check back soon.
            </p>
          </div>
        ) : (
          tree.subjects.map((subject) => (
            <section key={subject.subject}>
              <h2 className="mb-3 text-lg font-semibold text-gray-800">
                {subject.subject}
              </h2>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {subject.units.map((unit) => {
                  const status = statusMap.get(unit.unit_id) ?? "not_started";
                  const { icon: Icon, color } = STATUS_CONFIG[status];
                  return (
                    <div
                      key={unit.unit_id}
                      className="flex flex-col gap-3 rounded-lg border bg-white p-4 shadow-sm"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-sm leading-tight font-medium text-gray-900">
                          {unit.title}
                        </p>
                        <Icon className={cn("mt-0.5 h-4 w-4 shrink-0", color)} />
                      </div>
                      {unit.has_lab && (
                        <span className="flex items-center gap-1 text-xs text-purple-600">
                          <FlaskConical className="h-3 w-3" /> Lab
                        </span>
                      )}
                      <div className="mt-auto flex gap-2">
                        <LinkButton
                          href={`/lesson/${unit.unit_id}`}
                          size="sm"
                          variant="outline"
                          className="flex-1 justify-center text-xs"
                        >
                          Lesson
                        </LinkButton>
                        <LinkButton
                          href={`/quiz/${unit.unit_id}`}
                          size="sm"
                          className="flex-1 justify-center text-xs"
                        >
                          Quiz
                        </LinkButton>
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>
          ))
        )}
      </div>
    </div>
  );
}
