"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTeacher } from "@/lib/hooks/useTeacher";
import { getLibrary, updateAdoption, type AdoptionItem } from "@/lib/api/school-admin";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { LinkButton } from "@/components/ui/link-button";
import {
  Aisle,
  Shelf,
  BookSpine,
  BookOpen,
  ADOPTION_STATUS_ACCENT,
  deriveStreamAccent,
  deriveStreamKey,
} from "@/components/library";
import {
  BookMarked,
  CheckCircle2,
  PauseCircle,
  PlayCircle,
  PenLine,
  LayoutGrid,
  AlertTriangle,
} from "lucide-react";

// ── Adoption detail (rendered inside <BookOpen>) ─────────────────────────────

function AdoptionDetail({
  item,
  isAdmin,
  onToggle,
  toggling,
}: {
  item: AdoptionItem;
  isAdmin: boolean;
  onToggle: (item: AdoptionItem) => void;
  toggling: boolean;
}) {
  const isActive = item.status === "active";
  const isArchivedSource = !!item.is_source_archived;

  return (
    <div className="space-y-3">
      {/* Metadata pills */}
      <div className="flex flex-wrap items-center gap-2">
        {item.grade !== null && (
          <span className="rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-700">
            Grade {item.grade}
          </span>
        )}
        {item.year !== null && (
          <span className="rounded-full bg-stone-100 px-2 py-0.5 text-xs font-medium text-stone-600">
            {item.year}
          </span>
        )}
        {item.has_overrides && (
          <Badge className="border-blue-200 bg-blue-50 text-xs text-blue-700">
            <PenLine className="mr-1 h-3 w-3" />
            Customized
          </Badge>
        )}
        {!isActive && !isArchivedSource && (
          <Badge className="border-gray-200 bg-gray-50 text-xs text-gray-500">
            Deactivated
          </Badge>
        )}
        {isArchivedSource && (
          <Badge className="border-amber-300 bg-amber-100 text-xs text-amber-700">
            Archived by platform admin
          </Badge>
        )}
        <span className="text-xs text-gray-400">
          Adopted {new Date(item.adopted_at).toLocaleDateString()}
        </span>
      </div>

      {/* Notes */}
      {item.notes && <p className="text-xs text-gray-500 italic">{item.notes}</p>}

      {/* Archived source notice — replaces action buttons */}
      {isArchivedSource ? (
        <div className="rounded-md border border-amber-200 bg-amber-50 p-3">
          <div className="flex items-start gap-2">
            <AlertTriangle
              className="mt-0.5 h-4 w-4 shrink-0 text-amber-600"
              aria-hidden="true"
            />
            <div className="min-w-0">
              {item.archive_reason && (
                <p className="mb-1 text-xs font-medium text-amber-700">
                  Reason: {item.archive_reason}
                </p>
              )}
              <p className="text-xs text-amber-700">
                This curriculum has been archived by the platform. New imports are
                unavailable.
                {item.has_overrides &&
                  " Your customized content is preserved and students retain access."}
              </p>
            </div>
          </div>
        </div>
      ) : (
        <div className="flex flex-wrap items-center gap-2">
          <LinkButton
            href={`/school/content/adopt/${item.adoption_id}`}
            variant="outline"
            size="sm"
          >
            <PenLine className="mr-1.5 h-3.5 w-3.5" />
            {item.has_overrides ? "Edit content" : "Import & customize"}
          </LinkButton>
          {isAdmin && (
            <button
              type="button"
              onClick={() => onToggle(item)}
              disabled={toggling}
              className="inline-flex items-center gap-1.5 rounded-md border border-gray-200 px-2.5 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50 focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50"
              aria-label={isActive ? "Deactivate" : "Reactivate"}
            >
              {isActive ? (
                <>
                  <PauseCircle className="h-3.5 w-3.5 text-gray-500" aria-hidden="true" />
                  Deactivate
                </>
              ) : (
                <>
                  <PlayCircle className="h-3.5 w-3.5 text-green-600" aria-hidden="true" />
                  Reactivate
                </>
              )}
            </button>
          )}
        </div>
      )}
    </div>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function LibraryPage() {
  const teacher = useTeacher();
  const schoolId = teacher?.school_id ?? "";
  const isAdmin = teacher?.role === "school_admin";
  const queryClient = useQueryClient();
  const [togglingId, setTogglingId] = useState<string | null>(null);
  const [openAdoptionId, setOpenAdoptionId] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["library", schoolId],
    queryFn: () => getLibrary(schoolId),
    enabled: !!schoolId,
    staleTime: 60_000,
  });

  const toggleMutation = useMutation({
    mutationFn: ({ item }: { item: AdoptionItem }) =>
      updateAdoption(schoolId, item.adoption_id, {
        status: item.status === "active" ? "deactivated" : "active",
      }),
    onMutate: ({ item }) => setTogglingId(item.adoption_id),
    onSettled: () => {
      setTogglingId(null);
      queryClient.invalidateQueries({ queryKey: ["library", schoolId] });
    },
  });

  const adoptions = data?.adoptions ?? [];
  const archivedAdoptions = adoptions.filter((a) => a.is_source_archived);
  const activeAdoptions = adoptions.filter(
    (a) => !a.is_source_archived && a.status === "active",
  );
  const deactivatedAdoptions = adoptions.filter(
    (a) => !a.is_source_archived && a.status === "deactivated",
  );

  const onToggleSpine = (id: string) =>
    setOpenAdoptionId((cur) => (cur === id ? null : id));

  function renderAisle(
    label: string,
    ariaId: string,
    headingAccent: string,
    items: AdoptionItem[],
  ) {
    if (items.length === 0) return null;

    // Group items by grade; null grades collected together at the end.
    const byGrade = new Map<number | null, AdoptionItem[]>();
    for (const item of items) {
      const arr = byGrade.get(item.grade) ?? [];
      arr.push(item);
      byGrade.set(item.grade, arr);
    }
    const grades = Array.from(byGrade.keys()).sort((a, b) => {
      if (a === null) return 1;
      if (b === null) return -1;
      return a - b;
    });

    return (
      <Aisle subject={label} ariaId={ariaId} headingAccent={headingAccent}>
        <div className="space-y-5">
          {grades.map((grade) => {
            const inGrade = byGrade.get(grade) ?? [];
            const openInGrade =
              inGrade.find((a) => a.adoption_id === openAdoptionId) ?? null;
            const gradeLabel = grade === null ? "Ungraded" : `Grade ${grade}`;
            const gradeKey = grade === null ? "ungraded" : `g${grade}`;
            return (
              <div key={`${ariaId}-${gradeKey}`} className="space-y-2">
                <h3 className="text-xs font-semibold tracking-wide text-gray-500 uppercase">
                  {gradeLabel}
                </h3>
                <Shelf ariaLabel={`${label} ${gradeLabel} adoptions`}>
                  {inGrade.map((item) => (
                    <BookSpine
                      key={item.adoption_id}
                      unitId={item.adoption_id}
                      title={item.name}
                      subjectKey={deriveStreamKey(item.name)}
                      accentOverride={deriveStreamAccent(item.name)}
                      dim={item.is_source_archived || item.status !== "active"}
                      isOpen={openAdoptionId === item.adoption_id}
                      onToggle={onToggleSpine}
                    />
                  ))}
                </Shelf>
                {openInGrade ? (
                  <BookOpen
                    title={openInGrade.name}
                    subheading="Details"
                    onClose={() => setOpenAdoptionId(null)}
                  >
                    <AdoptionDetail
                      item={openInGrade}
                      isAdmin={isAdmin}
                      onToggle={(i) => toggleMutation.mutate({ item: i })}
                      toggling={togglingId === openInGrade.adoption_id}
                    />
                  </BookOpen>
                ) : null}
              </div>
            );
          })}
        </div>
      </Aisle>
    );
  }

  return (
    <div className="max-w-5xl space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <BookMarked className="h-6 w-6 text-indigo-600" />
          <h1 className="text-2xl font-bold text-gray-900">My Curricula</h1>
        </div>
        <LinkButton href="/school/catalog" size="sm">
          <LayoutGrid className="mr-1.5 h-4 w-4" />
          Browse catalog
        </LinkButton>
      </div>

      <p className="text-sm text-gray-500">
        Curricula your school has adopted from the platform catalog. Teachers can import
        and customize content from these packages. Assign packages to classrooms from the{" "}
        <Link
          href="/school/classrooms"
          className="text-indigo-600 underline-offset-2 hover:underline"
        >
          Classrooms
        </Link>{" "}
        page.
      </p>

      {/* Body */}
      {isLoading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-24 rounded-lg" />
          ))}
        </div>
      ) : adoptions.length === 0 ? (
        <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed border-gray-200 py-12 text-center">
          <CheckCircle2 className="h-8 w-8 text-gray-300" />
          <p className="text-sm font-medium text-gray-500">No curricula adopted yet</p>
          <p className="max-w-xs text-xs text-gray-400">
            Browse the platform catalog and add curricula to your library so teachers can
            import and customize content for their classes.
          </p>
          {isAdmin && (
            <LinkButton href="/school/catalog" size="sm" className="mt-2">
              <LayoutGrid className="mr-1.5 h-4 w-4" />
              Browse catalog
            </LinkButton>
          )}
        </div>
      ) : (
        <>
          {renderAisle(
            "Active",
            "aisle-active",
            ADOPTION_STATUS_ACCENT.active,
            activeAdoptions,
          )}
          {renderAisle(
            "Deactivated",
            "aisle-deactivated",
            ADOPTION_STATUS_ACCENT.deactivated,
            deactivatedAdoptions,
          )}
          {renderAisle(
            "Archived by platform",
            "aisle-archived",
            ADOPTION_STATUS_ACCENT.archived,
            archivedAdoptions,
          )}
        </>
      )}
    </div>
  );
}
