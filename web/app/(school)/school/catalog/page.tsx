"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTeacher } from "@/lib/hooks/useTeacher";
import {
  getCatalog,
  type CatalogEntry,
  type CatalogSubjectSummary,
} from "@/lib/api/school-admin";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  LayoutGrid,
  BookOpen,
  Layers,
  CheckCircle2,
  Circle,
  ChevronDown,
  ChevronRight,
} from "lucide-react";

const ALL_GRADES = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12];

// ── Subject row ────────────────────────────────────────────────────────────────

function SubjectRow({ s }: { s: CatalogSubjectSummary }) {
  return (
    <div className="flex items-center gap-3 py-1.5 text-sm">
      {s.has_content ? (
        <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-green-500" />
      ) : (
        <Circle className="h-3.5 w-3.5 shrink-0 text-gray-300" />
      )}
      <span className="flex-1 text-gray-700">
        {s.subject_name ?? s.subject}
      </span>
      <span className="text-xs text-gray-400">
        {s.unit_count} unit{s.unit_count !== 1 ? "s" : ""}
      </span>
    </div>
  );
}

// ── Catalog card ───────────────────────────────────────────────────────────────

function CatalogCard({ pkg }: { pkg: CatalogEntry }) {
  const [expanded, setExpanded] = useState(false);

  const readySubjects = pkg.subjects.filter((s) => s.has_content).length;

  return (
    <Card className="border shadow-sm">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-start justify-between gap-2 text-base">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-gray-900">{pkg.name}</span>
              <span className="rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-700">
                Grade {pkg.grade}
              </span>
              {pkg.is_default && (
                <Badge className="border-green-200 bg-green-50 text-xs text-green-700">
                  Platform
                </Badge>
              )}
            </div>
            <p className="mt-0.5 text-xs text-gray-400">
              {pkg.year} · {pkg.subject_count} subject{pkg.subject_count !== 1 ? "s" : ""} ·{" "}
              {pkg.unit_count} unit{pkg.unit_count !== 1 ? "s" : ""}
            </p>
          </div>

          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            className="shrink-0 rounded-md p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
            aria-label={expanded ? "Collapse subjects" : "Expand subjects"}
          >
            {expanded ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
          </button>
        </CardTitle>
      </CardHeader>

      <CardContent className="pt-0">
        {/* Content readiness bar */}
        <div className="mb-3 flex items-center gap-2">
          <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-gray-100">
            <div
              className="h-full rounded-full bg-green-400 transition-all"
              style={{
                width:
                  pkg.subject_count > 0
                    ? `${(readySubjects / pkg.subject_count) * 100}%`
                    : "0%",
              }}
            />
          </div>
          <span className="text-xs text-gray-400">
            {readySubjects}/{pkg.subject_count} ready
          </span>
        </div>

        {/* Subject list — expandable */}
        {expanded && pkg.subjects.length > 0 && (
          <div className="divide-y divide-gray-50">
            {pkg.subjects.map((s) => (
              <SubjectRow key={s.subject} s={s} />
            ))}
          </div>
        )}

        {expanded && pkg.subjects.length === 0 && (
          <p className="text-xs text-gray-400 italic">No subjects yet.</p>
        )}
      </CardContent>
    </Card>
  );
}

// ── Page ───────────────────────────────────────────────────────────────────────

export default function CatalogPage() {
  const teacher = useTeacher();
  const [gradeFilter, setGradeFilter] = useState<number | "">("");

  const { data, isLoading } = useQuery({
    queryKey: ["catalog", gradeFilter],
    queryFn: () => getCatalog(gradeFilter === "" ? undefined : gradeFilter),
    staleTime: 60_000,
    enabled: !!teacher,
  });

  const packages = data?.packages ?? [];

  return (
    <div className="max-w-3xl space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center gap-2">
        <LayoutGrid className="h-6 w-6 text-indigo-600" />
        <h1 className="text-2xl font-bold text-gray-900">Curriculum Catalog</h1>
      </div>

      <p className="text-sm text-gray-500">
        Platform-built curriculum packages available for assignment to your classrooms.
        Each package covers a full grade&apos;s STEM content across multiple subjects and units.
        Assign packages to classrooms from the{" "}
        <a href="/school/classrooms" className="text-indigo-600 underline-offset-2 hover:underline">
          Classrooms
        </a>{" "}
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

      {/* Package list */}
      {isLoading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-24 rounded-lg" />
          ))}
        </div>
      ) : packages.length > 0 ? (
        <div className="space-y-4">
          {packages.map((pkg) => (
            <CatalogCard key={pkg.curriculum_id} pkg={pkg} />
          ))}
        </div>
      ) : (
        <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed border-gray-200 py-12 text-center">
          <BookOpen className="h-8 w-8 text-gray-300" />
          <p className="text-sm text-gray-400">
            {gradeFilter !== ""
              ? `No platform packages found for Grade ${gradeFilter}.`
              : "No platform curriculum packages available yet."}
          </p>
        </div>
      )}

      {/* Legend */}
      <div className="flex items-center gap-6 border-t pt-4 text-xs text-gray-400">
        <span className="flex items-center gap-1.5">
          <CheckCircle2 className="h-3.5 w-3.5 text-green-500" />
          Content ready
        </span>
        <span className="flex items-center gap-1.5">
          <Circle className="h-3.5 w-3.5 text-gray-300" />
          Content pending
        </span>
        <span className="flex items-center gap-1.5">
          <Layers className="h-3.5 w-3.5 text-gray-300" />
          Readiness bar shows approved subjects
        </span>
      </div>
    </div>
  );
}
