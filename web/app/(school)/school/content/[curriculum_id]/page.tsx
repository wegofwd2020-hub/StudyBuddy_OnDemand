"use client";

import { Fragment, useState } from "react";
import { useParams, useSearchParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTeacher } from "@/lib/hooks/useTeacher";
import {
  listUnitOverrideStatus,
  importUnit,
  type UnitStatusItem,
  type UnitOverrideStatus,
} from "@/lib/api/school-admin";
import { Skeleton } from "@/components/ui/skeleton";
import { LinkButton } from "@/components/ui/link-button";
import {
  ArrowLeft,
  BookOpen,
  Download,
  Pencil,
  Eye,
  CheckCircle2,
} from "lucide-react";

// ── Badge ──────────────────────────────────────────────────────────────────────

type BadgeState =
  | "oob"
  | "imported"
  | "draft"
  | "pending_review"
  | "published"
  | "rejected";

const BADGE_STYLES: Record<BadgeState, string> = {
  oob: "bg-gray-100 text-gray-500",
  imported: "bg-yellow-50 text-yellow-700 border border-yellow-200",
  draft: "bg-orange-50 text-orange-700 border border-orange-200",
  pending_review: "bg-blue-50 text-blue-700 border border-blue-200",
  published: "bg-green-50 text-green-700 border border-green-200",
  rejected: "bg-red-50 text-red-700 border border-red-200",
};

const BADGE_LABELS: Record<BadgeState, string> = {
  oob: "OOB",
  imported: "Imported",
  draft: "Draft",
  pending_review: "Pending review",
  published: "Published",
  rejected: "Rejected",
};

function computeBadgeState(overrides: UnitOverrideStatus[]): BadgeState {
  if (overrides.length === 0) return "oob";

  const statuses = overrides.map((o) => o.review_status);

  if (statuses.includes("pending_review")) return "pending_review";
  if (statuses.includes("rejected")) return "rejected";

  const hasDraftEdited = overrides.some(
    (o) => o.review_status === "draft" && o.content_source !== "imported",
  );
  if (hasDraftEdited) return "draft";

  const hasDraftImported = overrides.some(
    (o) => o.review_status === "draft" && o.content_source === "imported",
  );
  if (hasDraftImported) return "imported";

  const hasPublished = overrides.some(
    (o) => o.review_status === "approved" && o.is_active,
  );
  if (hasPublished) return "published";

  return "oob";
}

function OverrideBadge({ overrides }: { overrides: UnitOverrideStatus[] }) {
  const state = computeBadgeState(overrides);
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${BADGE_STYLES[state]}`}
    >
      {BADGE_LABELS[state]}
    </span>
  );
}

// ── Unit row ───────────────────────────────────────────────────────────────────

function latestOverride(overrides: UnitOverrideStatus[]): UnitOverrideStatus | null {
  if (overrides.length === 0) return null;
  return overrides.reduce((a, b) =>
    new Date(a.edited_at) > new Date(b.edited_at) ? a : b,
  );
}

function UnitRow({
  unit,
  schoolId,
  curriculumId,
  adoptionId,
  onImported,
}: {
  unit: UnitStatusItem;
  schoolId: string;
  curriculumId: string;
  adoptionId: string;
  onImported: () => void;
}) {
  const state = computeBadgeState(unit.overrides);
  const latest = latestOverride(unit.overrides);

  const importMutation = useMutation({
    mutationFn: () => importUnit(schoolId, adoptionId, unit.unit_id),
    onSuccess: onImported,
  });

  const canImport = state === "oob" && !!adoptionId && unit.has_content;
  const noContent = state === "oob" && !!adoptionId && !unit.has_content;
  const canEdit = state === "imported" || state === "draft" || state === "rejected";
  const canView = state === "published" || state === "pending_review";

  return (
    <tr className="border-b border-gray-100 hover:bg-gray-50">
      <td className="py-3 pl-4 pr-3 text-sm font-medium text-gray-900">
        {unit.title}
      </td>
      <td className="px-3 py-3 text-sm text-gray-500">
        {unit.subject_name ?? unit.subject}
      </td>
      <td className="px-3 py-3">
        <OverrideBadge overrides={unit.overrides} />
      </td>
      <td className="px-3 py-3 text-sm text-gray-500 tabular-nums">
        {latest ? `v${latest.version_number}` : "—"}
      </td>
      <td className="px-3 py-3 text-sm text-gray-400">
        {latest?.last_edited_by_name ?? "—"}
      </td>
      <td className="px-3 py-3 text-xs text-gray-400">
        {latest
          ? new Date(latest.edited_at).toLocaleDateString(undefined, {
              month: "short",
              day: "numeric",
              year: "numeric",
            })
          : "—"}
      </td>
      <td className="py-3 pl-3 pr-4 text-right">
        <div className="flex items-center justify-end gap-2">
          {canImport && (
            <button
              type="button"
              onClick={() => importMutation.mutate()}
              disabled={importMutation.isPending}
              className="inline-flex items-center gap-1 rounded-md border border-gray-200 bg-white px-2.5 py-1 text-xs font-medium text-gray-600 shadow-sm hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Download className="h-3 w-3" />
              {importMutation.isPending ? "Importing…" : "Import"}
            </button>
          )}
          {noContent && (
            <span
              title="Content not yet generated for this unit"
              className="inline-flex cursor-not-allowed items-center gap-1 rounded-md border border-gray-100 bg-gray-50 px-2.5 py-1 text-xs font-medium text-gray-300"
            >
              <Download className="h-3 w-3" />
              Import
            </span>
          )}
          {canEdit && (
            <LinkButton
              href={`/school/content/${curriculumId}/units/${unit.unit_id}/edit`}
              size="sm"
              variant="outline"
              className="text-xs"
            >
              <Pencil className="mr-1 h-3 w-3" />
              Edit
            </LinkButton>
          )}
          {canView && (
            <LinkButton
              href={`/school/content/${curriculumId}/units/${unit.unit_id}/edit`}
              size="sm"
              variant="outline"
              className="text-xs"
            >
              <Eye className="mr-1 h-3 w-3" />
              View
            </LinkButton>
          )}
        </div>
      </td>
    </tr>
  );
}

// ── Page ───────────────────────────────────────────────────────────────────────

export default function ContentUnitsPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const router = useRouter();
  const curriculumId = params.curriculum_id as string;
  const adoptionId = searchParams.get("aid") ?? "";

  const teacher = useTeacher();
  const schoolId = teacher?.school_id ?? "";
  const queryClient = useQueryClient();

  const [importError, setImportError] = useState<string | null>(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ["unit-status", schoolId, curriculumId],
    queryFn: () => listUnitOverrideStatus(schoolId, curriculumId),
    enabled: !!schoolId && !!curriculumId,
    staleTime: 30_000,
  });

  function handleImported() {
    setImportError(null);
    queryClient.invalidateQueries({ queryKey: ["unit-status", schoolId, curriculumId] });
  }

  const units = data?.units ?? [];

  // Group by subject for section headers
  const subjects = Array.from(new Set(units.map((u) => u.subject)));

  return (
    <div className="max-w-5xl space-y-6 p-6">
      {/* Header */}
      <div className="flex items-start gap-4">
        <button
          type="button"
          onClick={() => router.back()}
          className="mt-0.5 rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
          aria-label="Back"
        >
          <ArrowLeft className="h-4 w-4" />
        </button>

        <div className="flex-1">
          <div className="flex items-center gap-2">
            <BookOpen className="h-5 w-5 text-indigo-600" />
            <h1 className="text-xl font-bold text-gray-900">
              {data?.curriculum_name ?? "Curriculum Content"}
            </h1>
            {data?.grade !== null && data?.grade !== undefined && (
              <span className="rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-700">
                Grade {data.grade}
              </span>
            )}
          </div>
          <p className="mt-1 text-sm text-gray-500">
            Import and customize units — each unit shows its current override
            status.
          </p>
        </div>
      </div>

      {/* Import error */}
      {importError && (
        <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {importError}
        </div>
      )}

      {/* No adoption_id warning */}
      {!adoptionId && (
        <div className="rounded-md border border-yellow-200 bg-yellow-50 px-4 py-3 text-sm text-yellow-800">
          Navigate here from{" "}
          <a href="/school/library" className="underline">
            Our Library
          </a>{" "}
          to enable Import actions.
        </div>
      )}

      {/* Table */}
      {isLoading ? (
        <div className="space-y-3">
          {[1, 2, 3, 4, 5].map((i) => (
            <Skeleton key={i} className="h-12 rounded-lg" />
          ))}
        </div>
      ) : error ? (
        <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          Failed to load unit status. Please try refreshing.
        </div>
      ) : units.length === 0 ? (
        <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed border-gray-200 py-12 text-center">
          <CheckCircle2 className="h-8 w-8 text-gray-300" />
          <p className="text-sm font-medium text-gray-500">No units found</p>
          <p className="max-w-xs text-xs text-gray-400">
            This curriculum has no units yet, or the content has not been
            generated.
          </p>
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
          <table className="min-w-full divide-y divide-gray-100">
            <thead className="bg-gray-50">
              <tr>
                <th
                  scope="col"
                  className="py-3 pl-4 pr-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500"
                >
                  Unit
                </th>
                <th
                  scope="col"
                  className="px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500"
                >
                  Subject
                </th>
                <th
                  scope="col"
                  className="px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500"
                >
                  Status
                </th>
                <th
                  scope="col"
                  className="px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500"
                >
                  Version
                </th>
                <th
                  scope="col"
                  className="px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500"
                >
                  Last edited by
                </th>
                <th
                  scope="col"
                  className="px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500"
                >
                  Last edited
                </th>
                <th scope="col" className="relative py-3 pl-3 pr-4">
                  <span className="sr-only">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {subjects.map((subject) => {
                const subjectUnits = units.filter((u) => u.subject === subject);
                const subjectName =
                  subjectUnits[0]?.subject_name ?? subject;
                return (
                  <Fragment key={`subj-${subject}`}>
                    <tr className="bg-gray-50">
                      <td
                        colSpan={7}
                        className="py-2 pl-4 pr-3 text-xs font-semibold uppercase tracking-wider text-gray-500"
                      >
                        {subjectName}
                      </td>
                    </tr>
                    {subjectUnits.map((unit) => (
                      <UnitRow
                        key={unit.unit_id}
                        unit={unit}
                        schoolId={schoolId}
                        curriculumId={curriculumId}
                        adoptionId={adoptionId}
                        onImported={handleImported}
                      />
                    ))}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Legend */}
      {units.length > 0 && (
        <div className="flex flex-wrap gap-3 text-xs text-gray-500">
          <span className="font-medium">Status:</span>
          {(
            [
              "oob",
              "imported",
              "draft",
              "pending_review",
              "published",
              "rejected",
            ] as BadgeState[]
          ).map((s) => (
            <span
              key={s}
              className={`inline-flex items-center rounded-full px-2 py-0.5 font-medium ${BADGE_STYLES[s]}`}
            >
              {BADGE_LABELS[s]}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
