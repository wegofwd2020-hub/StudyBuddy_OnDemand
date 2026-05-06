"use client";

import { useState } from "react";
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
} from "@/components/library";

type SubjectUnit = { unit_id: string; title: string; has_lab?: boolean };

function SubjectUnitList({ units }: { units: SubjectUnit[] }) {
  if (units.length === 0) {
    return (
      <p className="text-xs italic text-gray-400">No units in this subject yet.</p>
    );
  }
  return (
    <ol role="list" className="divide-y divide-gray-100">
      {units.map((unit) => (
        <li
          key={unit.unit_id}
          className="flex items-center justify-between gap-3 py-2"
        >
          <div className="flex min-w-0 items-center gap-2">
            <span className="truncate text-sm text-gray-700">{unit.title}</span>
            {unit.has_lab && (
              <FlaskConical
                className="h-3.5 w-3.5 shrink-0 text-purple-500"
                aria-hidden="true"
              />
            )}
          </div>
          <div className="flex shrink-0 items-center gap-1">
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
          </div>
        </li>
      ))}
    </ol>
  );
}

export default function SubjectsPage() {
  const { data: tree, isLoading, isError } = useCurriculumTree();
  const [openSubject, setOpenSubject] = useState<string | null>(null);

  const subjects = tree?.subjects ?? [];
  const open = subjects.find((s) => s.subject === openSubject) ?? null;

  return (
    <div className="flex flex-col">
      <OfflineBanner />
      <div className="max-w-5xl space-y-6 p-6">
        <h1 className="text-2xl font-bold text-gray-900">Subjects</h1>

        {isLoading && (
          <div className="flex gap-3">
            {[...Array(4)].map((_, i) => (
              <Skeleton key={i} className="h-56 w-24 rounded-md" />
            ))}
          </div>
        )}

        {isError && (
          <p className="text-sm text-red-500">
            Could not load curriculum. Please retry.
          </p>
        )}

        {!isLoading && !isError && subjects.length === 0 && (
          <p className="text-sm text-gray-500">
            Your curriculum hasn&apos;t been published yet.
          </p>
        )}

        {!isLoading && !isError && subjects.length > 0 && (
          <>
            <Shelf ariaLabel="Subjects">
              {subjects.map((subject) => (
                <BookSpine
                  key={subject.subject}
                  unitId={subject.subject}
                  title={subject.subject}
                  subjectKey={subject.subject}
                  accentOverride={deriveSubjectAccent(subject.subject)}
                  isOpen={openSubject === subject.subject}
                  onToggle={(id) =>
                    setOpenSubject((cur) => (cur === id ? null : id))
                  }
                />
              ))}
            </Shelf>
            {open ? (
              <BookOpen
                title={open.subject}
                subheading={`${open.units.length} unit${open.units.length !== 1 ? "s" : ""}`}
                onClose={() => setOpenSubject(null)}
              >
                <SubjectUnitList units={open.units} />
              </BookOpen>
            ) : null}
          </>
        )}
      </div>
    </div>
  );
}
