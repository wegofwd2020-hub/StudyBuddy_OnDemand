"use client";

import { useState } from "react";
import { useCurriculumTree } from "@/lib/hooks/useCurriculumTree";
import { useProgressHistory } from "@/lib/hooks/useProgress";
import { Skeleton } from "@/components/ui/skeleton";
import { OfflineBanner } from "@/components/student/OfflineBanner";
import { useTranslations } from "next-intl";
import { BookOpen as BookOpenIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import type { UnitStatus } from "@/lib/types/api";
import {
  Aisle,
  Shelf,
  BookSpine,
  BookOpen,
  Toc,
  STATUS_CONFIG,
  subjectAriaId,
} from "@/components/library";

export default function CurriculumMapPage() {
  const t = useTranslations("curriculum_map_screen");
  const { data: tree, isLoading: treeLoading } = useCurriculumTree();
  const { data: history, isLoading: histLoading } = useProgressHistory(100);
  const [openUnitId, setOpenUnitId] = useState<string | null>(null);

  const loading = treeLoading || histLoading;

  const statusMap = new Map<string, UnitStatus>();
  history?.unit_progress?.forEach((up) => statusMap.set(up.unit_id, up.status));

  return (
    <div className="flex flex-col">
      <OfflineBanner />
      <div className="max-w-5xl space-y-8 p-6">
        <h1 className="text-2xl font-bold text-gray-900">{t("title")}</h1>

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
        ) : !tree?.subjects?.length ? (
          <div className="rounded-xl border border-gray-200 bg-white py-16 text-center">
            <BookOpenIcon className="mx-auto mb-3 h-10 w-10 text-gray-300" />
            <p className="mb-1 text-sm font-medium text-gray-600">{t("no_units")}</p>
            <p className="text-xs text-gray-400">
              Your curriculum hasn&apos;t been published yet. Check back soon.
            </p>
          </div>
        ) : (
          tree.subjects.map((subject) => {
            const open = subject.units.find((u) => u.unit_id === openUnitId);
            return (
              <Aisle
                key={subject.subject}
                subject={subject.subject}
                ariaId={subjectAriaId(subject.subject)}
              >
                <Shelf ariaLabel={`${subject.subject} units`}>
                  {subject.units.map((unit) => (
                    <BookSpine
                      key={unit.unit_id}
                      unitId={unit.unit_id}
                      title={unit.title}
                      subjectKey={subject.subject}
                      status={statusMap.get(unit.unit_id) ?? "not_started"}
                      hasLab={unit.has_lab}
                      isOpen={openUnitId === unit.unit_id}
                      onToggle={(id) =>
                        setOpenUnitId((cur) => (cur === id ? null : id))
                      }
                    />
                  ))}
                </Shelf>
                {open ? (
                  <BookOpen
                    title={open.title}
                    onClose={() => setOpenUnitId(null)}
                  >
                    <Toc unitId={open.unit_id} hasLab={open.has_lab} />
                  </BookOpen>
                ) : null}
              </Aisle>
            );
          })
        )}
      </div>
    </div>
  );
}
