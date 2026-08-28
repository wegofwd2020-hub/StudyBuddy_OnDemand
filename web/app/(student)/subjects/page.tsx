"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useCurriculumTree } from "@/lib/hooks/useCurriculumTree";
import { LinkButton } from "@/components/ui/link-button";
import { Skeleton } from "@/components/ui/skeleton";
import { FlaskConical } from "lucide-react";
import { OfflineBanner } from "@/components/student/OfflineBanner";
import {
  Shelf,
  BookSpine,
  BookOpen,
  deriveSubjectAccent,
  STATUS_CONFIG,
} from "@/components/library";
import { useUnitStatuses } from "@/lib/hooks/useProgressMap";
import { cn } from "@/lib/utils";
import type { UnitStatus } from "@/lib/types/api";

type SubjectUnit = {
  unit_id: string;
  title: string;
  has_lab?: boolean;
  has_content?: boolean;
};

/**
 * Which units are done, and which are not (#677).
 *
 * Venki: *"In technology it says 3 of 5 units, can you highlight which 2 units
 * not taken yet."* The list showed every unit identically, so the count on the
 * dashboard could not be reconciled with anything on screen.
 *
 * Uses the shared STATUS_CONFIG, so this page and the Curriculum Map cannot
 * drift into describing the same unit differently — the two now read one
 * server-side status (#675).
 */
function UnitStatusMark({ status }: { status: UnitStatus }) {
  const { icon: Icon, color, label } = STATUS_CONFIG[status];
  return (
    <span className="flex shrink-0 items-center gap-1" title={label}>
      <Icon className={cn("h-3.5 w-3.5", color)} aria-hidden="true" />
      <span className="sr-only">{label}</span>
    </span>
  );
}

function SubjectUnitList({
  units,
  statusByUnit,
}: {
  units: SubjectUnit[];
  statusByUnit: Map<string, UnitStatus>;
}) {
  if (units.length === 0) {
    return <p className="text-xs text-gray-400 italic">No units in this subject yet.</p>;
  }
  return (
    <ol role="list" className="divide-y divide-gray-100">
      {units.map((unit) => {
        // Only an explicit false disables selection — undefined means the
        // backend didn't flag availability, so keep the unit clickable.
        const unavailable = unit.has_content === false;
        return (
          <li key={unit.unit_id} className="flex items-center justify-between gap-3 py-2">
            <div className="flex min-w-0 items-center gap-2">
              <UnitStatusMark status={statusByUnit.get(unit.unit_id) ?? "not_started"} />
              <span
                className={`truncate text-sm ${unavailable ? "text-gray-400" : "text-gray-700"}`}
              >
                {unit.title}
              </span>
              {unit.has_lab && (
                <FlaskConical
                  className="h-3.5 w-3.5 shrink-0 text-purple-500"
                  aria-hidden="true"
                />
              )}
            </div>
            <div className="flex shrink-0 items-center gap-1">
              {unavailable ? (
                <span
                  className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-500"
                  title="This unit's content hasn't been published yet."
                >
                  Coming soon
                </span>
              ) : (
                <>
                  <LinkButton
                    href={`/lesson/${unit.unit_id}`}
                    variant="ghost"
                    size="sm"
                    className="h-7 text-xs"
                  >
                    Lesson
                  </LinkButton>
                  <LinkButton
                    href={`/quiz/${unit.unit_id}`}
                    variant="ghost"
                    size="sm"
                    className="h-7 text-xs"
                  >
                    Quiz
                  </LinkButton>
                </>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}

export default function SubjectsPage() {
  const { data: tree, isLoading, isError } = useCurriculumTree();
  const { statusByUnit } = useUnitStatuses();
  const searchParams = useSearchParams();
  const [openSubject, setOpenSubject] = useState<string | null>(null);

  // Deep link from the dashboard's subject card (#677): /subjects?subject=X
  // opens that subject rather than dropping the student on a closed shelf and
  // making them find it again.
  const requested = searchParams.get("subject");
  useEffect(() => {
    if (requested) setOpenSubject(requested);
  }, [requested]);

  const subjects = tree?.subjects ?? [];
  const open = subjects.find((s) => s.subject === openSubject) ?? null;

  return (
    <div className="flex flex-col">
      <OfflineBanner />
      <div className="max-w-5xl space-y-6 p-6">
        <div className="space-y-1">
          <h1 className="text-2xl font-bold text-gray-900">Subjects</h1>
          <p className="text-sm text-gray-500">
            Browse every subject and open a lesson or quiz. To see how far you&apos;ve
            come, visit the Curriculum Map.
          </p>
        </div>

        {isLoading && (
          <div className="flex gap-3">
            {[...Array(4)].map((_, i) => (
              <Skeleton key={i} className="h-56 w-24 rounded-md" />
            ))}
          </div>
        )}

        {isError && (
          <p className="text-sm text-red-500">Could not load curriculum. Please retry.</p>
        )}

        {!isLoading && !isError && subjects.length === 0 && (
          <p className="text-sm text-gray-500">
            Your curriculum hasn&apos;t been published yet.
          </p>
        )}

        {!isLoading && !isError && subjects.length > 0 && (
          <>
            {/* Same legend and vocabulary as the Curriculum Map — one status,
                described one way. */}
            <div className="flex flex-wrap gap-4 text-xs text-gray-500">
              {Object.entries(STATUS_CONFIG).map(
                ([status, { icon: Icon, color, label }]) => (
                  <span key={status} className="flex items-center gap-1.5">
                    <Icon className={cn("h-3.5 w-3.5", color)} aria-hidden="true" />
                    {label}
                  </span>
                ),
              )}
            </div>
            <Shelf ariaLabel="Subjects">
              {subjects.map((subject) => (
                <BookSpine
                  key={subject.subject}
                  unitId={subject.subject}
                  title={subject.subject}
                  subjectKey={subject.subject}
                  accentOverride={deriveSubjectAccent(subject.subject)}
                  isOpen={openSubject === subject.subject}
                  onToggle={(id) => setOpenSubject((cur) => (cur === id ? null : id))}
                />
              ))}
            </Shelf>
            {open ? (
              <BookOpen
                title={open.subject}
                subheading={`${open.units.length} unit${open.units.length !== 1 ? "s" : ""}`}
                onClose={() => setOpenSubject(null)}
              >
                <SubjectUnitList units={open.units} statusByUnit={statusByUnit} />
              </BookOpen>
            ) : null}
          </>
        )}
      </div>
    </div>
  );
}
