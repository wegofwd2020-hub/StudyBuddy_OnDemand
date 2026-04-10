"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { useTeacher } from "@/lib/hooks/useTeacher";
import { getSchoolContentVersion } from "@/lib/api/school-admin";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { ArrowLeft, BookOpen, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

const STATUS_STYLE: Record<string, string> = {
  approved: "bg-green-50 text-green-700 border-green-200",
  published: "bg-blue-50 text-blue-700 border-blue-100",
  in_review: "bg-yellow-50 text-yellow-700 border-yellow-100",
  pending: "bg-gray-100 text-gray-500 border-gray-200",
  ready_for_review: "bg-orange-50 text-orange-700 border-orange-200",
  rejected: "bg-red-50 text-red-700 border-red-200",
};

export default function SchoolContentVersionPage() {
  const params = useParams();
  const versionId = params.version_id as string;
  const teacher = useTeacher();
  const schoolId = teacher?.school_id ?? "";

  const { data: version, isLoading } = useQuery({
    queryKey: ["school-content-version", schoolId, versionId],
    queryFn: () => getSchoolContentVersion(schoolId, versionId),
    enabled: !!schoolId && !!versionId,
    staleTime: 60_000,
  });

  return (
    <div className="max-w-3xl space-y-6 p-6">
      <div className="flex items-center gap-2">
        <Link
          href="/school/curriculum/content"
          className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-800"
        >
          <ArrowLeft className="h-4 w-4" />
          Back
        </Link>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          <Skeleton className="h-10 w-64 rounded" />
          <Skeleton className="h-4 w-40 rounded" />
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-14 rounded-lg" />
          ))}
        </div>
      ) : !version ? (
        <p className="text-sm text-gray-400 italic">Content version not found.</p>
      ) : (
        <>
          <div>
            <div className="flex items-center gap-2">
              <BookOpen className="h-5 w-5 text-indigo-600" />
              <h1 className="text-xl font-bold text-gray-900">
                {version.subject_name ?? version.subject}
              </h1>
              <Badge
                className={cn(
                  "text-xs",
                  STATUS_STYLE[version.status] ?? "bg-gray-100 text-gray-500",
                )}
              >
                {version.status.replace(/_/g, " ")}
              </Badge>
            </div>
            <p className="mt-1 text-sm text-gray-500">
              Grade {version.grade} · {version.curriculum_name} · v{version.version_number} ·{" "}
              {version.units.length} unit{version.units.length !== 1 ? "s" : ""}
            </p>
          </div>

          <section>
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500">
              Units
            </h2>
            {version.units.length === 0 ? (
              <p className="text-sm text-gray-400 italic">No units found.</p>
            ) : (
              <div className="space-y-2">
                {version.units.map((unit, idx) => (
                  <Link
                    key={unit.unit_id}
                    href={`/school/curriculum/content/${versionId}/unit/${unit.unit_id}`}
                    className="flex items-center justify-between rounded-lg border bg-white p-4 shadow-sm transition-colors hover:bg-indigo-50"
                  >
                    <div className="flex items-center gap-3">
                      <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-xs font-medium text-indigo-700">
                        {idx + 1}
                      </span>
                      <span className="font-medium text-gray-800">{unit.title}</span>
                    </div>
                    <ChevronRight className="h-4 w-4 shrink-0 text-gray-400" />
                  </Link>
                ))}
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}
