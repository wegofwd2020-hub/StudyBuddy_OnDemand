"use client";

import { useCurriculumTree } from "@/lib/hooks/useCurriculumTree";
import { LinkButton } from "@/components/ui/link-button";
import { Skeleton } from "@/components/ui/skeleton";
import { FlaskConical } from "lucide-react";
import { OfflineBanner } from "@/components/student/OfflineBanner";
import { useSubjectPalette } from "@/lib/theme/SchoolThemeContext";

// ── Per-subject card — uses theme palette for tinted header ───────────────────

type SubjectData = {
  subject: string;
  units: { unit_id: string; title: string; has_lab?: boolean }[];
};

function SubjectCard({ subject }: { subject: SubjectData }) {
  const palette = useSubjectPalette(subject.subject);

  return (
    <div
      className="overflow-hidden rounded-xl border shadow-sm"
      style={{ borderColor: palette.border }}
    >
      <div className="px-5 py-4" style={{ background: palette.bg1 }}>
        <h2 className="text-base font-bold" style={{ color: palette.ink }}>
          {subject.subject}
        </h2>
        <p className="text-xs" style={{ color: palette.ink, opacity: 0.65 }}>
          {subject.units.length} unit{subject.units.length !== 1 ? "s" : ""}
        </p>
      </div>

      <div className="divide-y bg-white">
        {subject.units.map((unit) => (
          <div
            key={unit.unit_id}
            className="flex items-center justify-between px-5 py-2"
          >
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-700">{unit.title}</span>
              {unit.has_lab && (
                <FlaskConical className="h-3.5 w-3.5 text-purple-500" />
              )}
            </div>
            <div className="flex items-center gap-1">
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
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function SubjectsPage() {
  const { data: tree, isLoading, isError } = useCurriculumTree();

  return (
    <div className="flex flex-col">
      <OfflineBanner />
      <div className="max-w-5xl space-y-6 p-6">
        <h1 className="text-2xl font-bold text-gray-900">Subjects</h1>

        {isLoading && (
          <div className="grid gap-4 sm:grid-cols-2">
            {[...Array(4)].map((_, i) => (
              <Skeleton key={i} className="h-48 rounded-xl" />
            ))}
          </div>
        )}

        {isError && (
          <p className="text-sm text-red-500">Could not load curriculum. Please retry.</p>
        )}

        {tree?.subjects && (
          <div className="grid gap-6 sm:grid-cols-2">
            {tree.subjects.map((subject) => (
              <SubjectCard key={subject.subject} subject={subject} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
