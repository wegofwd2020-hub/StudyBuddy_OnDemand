"use client";

import { useState } from "react";
import { useCurriculumTree } from "@/lib/hooks/useCurriculumTree";
import { useUnitStatuses } from "@/lib/hooks/useProgressMap";
import { Skeleton } from "@/components/ui/skeleton";
import { OfflineBanner } from "@/components/student/OfflineBanner";
import { useTranslations } from "next-intl";
import { BookOpen as BookOpenIcon } from "lucide-react";
import { cn } from "@/lib/utils";
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
  // Status comes from the server (#677). It used to be derived here in the
  // browser from quiz sessions alone — a separate definition with no lesson
  // input, which is why #675's fix was invisible on this very screen.
  const { statusByUnit, isLoading: statusLoading } = useUnitStatuses();
  const [openUnitId, setOpenUnitId] = useState<string | null>(null);

  const loading = treeLoading || statusLoading;

  return (
    <div className="flex flex-col">
      <OfflineBanner />
      <div className="max-w-5xl space-y-8 p-6">
        <div className="space-y-1">
          <h1 className="text-2xl font-bold text-gray-900">{t("title")}</h1>
          <p className="text-sm text-gray-500">{t("subtitle")}</p>
        </div>

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
                      status={statusByUnit.get(unit.unit_id) ?? "not_started"}
                      hasLab={unit.has_lab}
                      dim={unit.has_content === false}
                      isOpen={openUnitId === unit.unit_id}
                      onToggle={(id) => setOpenUnitId((cur) => (cur === id ? null : id))}
                    />
                  ))}
                </Shelf>
                {open ? (
                  <BookOpen title={open.title} onClose={() => setOpenUnitId(null)}>
                    {open.has_content === false ? (
                      <p className="text-sm text-gray-500">
                        This unit&apos;s content hasn&apos;t been published yet. Check
                        back soon.
                      </p>
                    ) : (
                      <Toc unitId={open.unit_id} hasLab={open.has_lab} />
                    )}
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
