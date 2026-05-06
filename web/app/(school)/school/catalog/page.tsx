"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTeacher } from "@/lib/hooks/useTeacher";
import {
  getCatalog,
  getLibrary,
  adoptCurriculum,
  type CatalogEntry,
} from "@/lib/api/school-admin";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Aisle,
  Shelf,
  BookSpine,
  BookOpen,
  deriveStreamAccent,
  deriveStreamKey,
} from "@/components/library";
import {
  LayoutGrid,
  BookOpen as BookOpenIcon,
  CheckCircle2,
  Circle,
  BookMarked,
  Plus,
} from "lucide-react";

const ALL_GRADES = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12];

// ── Catalog detail (rendered inside <BookOpen>) ─────────────────────────────

function CatalogDetail({
  pkg,
  adopted,
  isAdmin,
  onAdopt,
  adopting,
}: {
  pkg: CatalogEntry;
  adopted: boolean;
  isAdmin: boolean;
  onAdopt: (curriculumId: string) => void;
  adopting: boolean;
}) {
  const readySubjects = pkg.subjects.filter((s) => s.has_content).length;
  const readinessPct =
    pkg.subject_count > 0 ? (readySubjects / pkg.subject_count) * 100 : 0;

  return (
    <div className="space-y-3">
      {/* Metadata pills */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded-full bg-stone-100 px-2 py-0.5 text-xs font-medium text-stone-600">
          {pkg.year}
        </span>
        <span className="text-xs text-gray-500">
          {pkg.subject_count} subject{pkg.subject_count !== 1 ? "s" : ""}
        </span>
        <span className="text-xs text-gray-500">
          {pkg.unit_count} unit{pkg.unit_count !== 1 ? "s" : ""}
        </span>
        {pkg.is_default && (
          <Badge className="border-green-200 bg-green-50 text-xs text-green-700">
            Platform
          </Badge>
        )}
      </div>

      {/* Readiness bar */}
      <div className="flex items-center gap-2">
        <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-gray-100">
          <div
            className="h-full rounded-full bg-green-400 transition-all"
            style={{ width: `${readinessPct}%` }}
          />
        </div>
        <span className="text-xs text-gray-400">
          {readySubjects}/{pkg.subject_count} ready
        </span>
      </div>

      {/* Subject list */}
      {pkg.subjects.length > 0 ? (
        <ul className="divide-y divide-gray-50">
          {pkg.subjects.map((s) => (
            <li
              key={s.subject}
              className="flex items-center gap-3 py-1.5 text-sm"
            >
              {s.has_content ? (
                <CheckCircle2
                  className="h-3.5 w-3.5 shrink-0 text-green-500"
                  aria-hidden="true"
                />
              ) : (
                <Circle
                  className="h-3.5 w-3.5 shrink-0 text-gray-300"
                  aria-hidden="true"
                />
              )}
              <span className="flex-1 text-gray-700">
                {s.subject_name ?? s.subject}
              </span>
              <span className="text-xs text-gray-400">
                {s.unit_count} unit{s.unit_count !== 1 ? "s" : ""}
              </span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-xs italic text-gray-400">No subjects yet.</p>
      )}

      {/* Adopt action */}
      {isAdmin && (
        <div className="pt-1">
          {adopted ? (
            <span className="inline-flex items-center gap-1.5 rounded-md bg-green-50 px-2.5 py-1.5 text-xs font-medium text-green-700">
              <BookMarked className="h-3.5 w-3.5" aria-hidden="true" />
              In library
            </span>
          ) : (
            <button
              type="button"
              onClick={() => onAdopt(pkg.curriculum_id)}
              disabled={adopting}
              className="inline-flex items-center gap-1.5 rounded-md bg-indigo-50 px-2.5 py-1.5 text-xs font-medium text-indigo-700 hover:bg-indigo-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Plus className="h-3.5 w-3.5" aria-hidden="true" />
              {adopting ? "Adding…" : "Add to library"}
            </button>
          )}
        </div>
      )}
    </div>
  );
}

// ── Page ───────────────────────────────────────────────────────────────────────

export default function CatalogPage() {
  const teacher = useTeacher();
  const schoolId = teacher?.school_id ?? "";
  const isAdmin = teacher?.role === "school_admin";
  const queryClient = useQueryClient();
  const [gradeFilter, setGradeFilter] = useState<number | "">("");
  const [adoptingId, setAdoptingId] = useState<string | null>(null);
  const [openCurriculumId, setOpenCurriculumId] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["catalog", gradeFilter],
    queryFn: () => getCatalog(gradeFilter === "" ? undefined : gradeFilter),
    staleTime: 60_000,
    enabled: !!teacher,
  });

  const { data: libraryData } = useQuery({
    queryKey: ["library", schoolId],
    queryFn: () => getLibrary(schoolId),
    enabled: !!schoolId && isAdmin,
    staleTime: 60_000,
  });

  const adoptedIds = new Set(
    (libraryData?.adoptions ?? []).map((a) => a.curriculum_id),
  );

  const adoptMutation = useMutation({
    mutationFn: (curriculumId: string) => adoptCurriculum(schoolId, curriculumId),
    onMutate: (curriculumId) => setAdoptingId(curriculumId),
    onSettled: () => {
      setAdoptingId(null);
      queryClient.invalidateQueries({ queryKey: ["library", schoolId] });
    },
  });

  const packages = data?.packages ?? [];

  const onToggleSpine = (id: string) =>
    setOpenCurriculumId((cur) => (cur === id ? null : id));

  // Group packages by grade; null grades collected at the end.
  const byGrade = new Map<number | null, CatalogEntry[]>();
  for (const pkg of packages) {
    const key: number | null = pkg.grade ?? null;
    const arr = byGrade.get(key) ?? [];
    arr.push(pkg);
    byGrade.set(key, arr);
  }
  const grades = Array.from(byGrade.keys()).sort((a, b) => {
    if (a === null) return 1;
    if (b === null) return -1;
    return a - b;
  });

  return (
    <div className="max-w-5xl space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center gap-2">
        <LayoutGrid className="h-6 w-6 text-indigo-600" />
        <h1 className="text-2xl font-bold text-gray-900">Curriculum Catalog</h1>
      </div>

      <p className="text-sm text-gray-500">
        Platform-built curriculum packages available for assignment to your classrooms.
        Each package covers a full grade&apos;s content across multiple subjects and units.
        Assign packages to classrooms from the{" "}
        <Link
          href="/school/classrooms"
          className="text-indigo-600 underline-offset-2 hover:underline"
        >
          Classrooms
        </Link>{" "}
        page.
      </p>

      {/* Grade filter */}
      <div className="flex items-center gap-3">
        <label htmlFor="grade_filter" className="text-sm font-medium text-gray-700">
          Filter by grade
        </label>
        <select
          id="grade_filter"
          value={gradeFilter}
          onChange={(e) =>
            setGradeFilter(e.target.value === "" ? "" : Number(e.target.value))
          }
          className="h-9 rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
        >
          <option value="">All grades</option>
          {ALL_GRADES.map((g) => (
            <option key={g} value={g}>
              Grade {g}
            </option>
          ))}
        </select>

        {data && (
          <span className="text-sm text-gray-400">
            {data.total} package{data.total !== 1 ? "s" : ""}
          </span>
        )}
      </div>

      {/* Body */}
      {isLoading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-24 rounded-lg" />
          ))}
        </div>
      ) : packages.length === 0 ? (
        <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed border-gray-200 py-12 text-center">
          <BookOpenIcon className="h-8 w-8 text-gray-300" />
          <p className="text-sm text-gray-400">
            {gradeFilter !== ""
              ? `No platform packages found for Grade ${gradeFilter}.`
              : "No platform curriculum packages available yet."}
          </p>
        </div>
      ) : (
        <>
          {grades.map((grade) => {
            const inGrade = byGrade.get(grade) ?? [];
            const gradeLabel = grade === null ? "Ungraded" : `Grade ${grade}`;
            const gradeKey = grade === null ? "ungraded" : `g${grade}`;
            const openInGrade =
              inGrade.find((p) => p.curriculum_id === openCurriculumId) ?? null;
            return (
              <Aisle
                key={`aisle-grade-${gradeKey}`}
                subject={gradeLabel}
                ariaId={`aisle-grade-${gradeKey}`}
              >
                <Shelf ariaLabel={`${gradeLabel} curriculum packages`}>
                  {inGrade.map((pkg) => (
                    <BookSpine
                      key={pkg.curriculum_id}
                      unitId={pkg.curriculum_id}
                      title={pkg.name}
                      subjectKey={deriveStreamKey(pkg.name)}
                      accentOverride={deriveStreamAccent(pkg.name)}
                      isOpen={openCurriculumId === pkg.curriculum_id}
                      onToggle={onToggleSpine}
                    />
                  ))}
                </Shelf>
                {openInGrade ? (
                  <BookOpen
                    title={openInGrade.name}
                    subheading="Details"
                    onClose={() => setOpenCurriculumId(null)}
                  >
                    <CatalogDetail
                      pkg={openInGrade}
                      adopted={adoptedIds.has(openInGrade.curriculum_id)}
                      isAdmin={isAdmin}
                      onAdopt={(id) => adoptMutation.mutate(id)}
                      adopting={adoptingId === openInGrade.curriculum_id}
                    />
                  </BookOpen>
                ) : null}
              </Aisle>
            );
          })}
        </>
      )}
    </div>
  );
}
