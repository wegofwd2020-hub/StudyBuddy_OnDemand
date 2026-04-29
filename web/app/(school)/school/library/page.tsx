"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTeacher } from "@/lib/hooks/useTeacher";
import {
  getLibrary,
  updateAdoption,
  type AdoptionItem,
} from "@/lib/api/school-admin";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { LinkButton } from "@/components/ui/link-button";
import {
  BookMarked,
  CheckCircle2,
  PauseCircle,
  PlayCircle,
  PenLine,
  LayoutGrid,
} from "lucide-react";

// ── Adoption card ─────────────────────────────────────────────────────────────

function AdoptionCard({
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

  return (
    <Card className={`border shadow-sm ${!isActive ? "opacity-60" : ""}`}>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-start justify-between gap-2 text-base">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-semibold text-gray-900">{item.name}</span>
              {item.grade !== null && (
                <span className="rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-700">
                  Grade {item.grade}
                </span>
              )}
              {item.year !== null && (
                <span className="text-xs text-gray-400">{item.year}</span>
              )}
              {item.has_overrides && (
                <Badge className="border-blue-200 bg-blue-50 text-xs text-blue-700">
                  <PenLine className="mr-1 h-3 w-3" />
                  Customized
                </Badge>
              )}
              {!isActive && (
                <Badge className="border-gray-200 bg-gray-50 text-xs text-gray-500">
                  Deactivated
                </Badge>
              )}
            </div>
            {item.notes && (
              <p className="mt-1 text-xs text-gray-400 italic">{item.notes}</p>
            )}
          </div>

          {isAdmin && (
            <button
              type="button"
              onClick={() => onToggle(item)}
              disabled={toggling}
              className="shrink-0 rounded-md p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 disabled:cursor-not-allowed"
              aria-label={isActive ? "Deactivate" : "Reactivate"}
              title={isActive ? "Deactivate" : "Reactivate"}
            >
              {isActive ? (
                <PauseCircle className="h-4 w-4 text-gray-400" />
              ) : (
                <PlayCircle className="h-4 w-4 text-green-500" />
              )}
            </button>
          )}
        </CardTitle>
      </CardHeader>

      <CardContent className="pt-0">
        <div className="flex flex-wrap items-center gap-3">
          <LinkButton
            href={`/school/content/adopt/${item.adoption_id}`}
            variant="outline"
            size="sm"
          >
            <PenLine className="mr-1.5 h-3.5 w-3.5" />
            {item.has_overrides ? "Edit content" : "Import & customize"}
          </LinkButton>
          <span className="text-xs text-gray-400">
            Adopted {new Date(item.adopted_at).toLocaleDateString()}
          </span>
        </div>
      </CardContent>
    </Card>
  );
}

// ── Page ───────────────────────────────────────────────────────────────────────

export default function LibraryPage() {
  const teacher = useTeacher();
  const schoolId = teacher?.school_id ?? "";
  const isAdmin = teacher?.role === "school_admin";
  const queryClient = useQueryClient();
  const [togglingId, setTogglingId] = useState<string | null>(null);

  const [showDeactivated, setShowDeactivated] = useState(false);

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
  const visible = adoptions.filter(
    (a) => showDeactivated || a.status === "active",
  );
  const deactivatedCount = adoptions.filter((a) => a.status === "deactivated").length;

  return (
    <div className="max-w-3xl space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <BookMarked className="h-6 w-6 text-indigo-600" />
          <h1 className="text-2xl font-bold text-gray-900">Our Library</h1>
        </div>
        <LinkButton href="/school/catalog" size="sm">
          <LayoutGrid className="mr-1.5 h-4 w-4" />
          Browse catalog
        </LinkButton>
      </div>

      <p className="text-sm text-gray-500">
        Curricula your school has adopted from the platform catalog. Teachers can import
        and customize content from these packages. Assign packages to classrooms from
        the{" "}
        <a
          href="/school/classrooms"
          className="text-indigo-600 underline-offset-2 hover:underline"
        >
          Classrooms
        </a>{" "}
        page.
      </p>

      {/* Deactivated toggle */}
      {deactivatedCount > 0 && (
        <button
          type="button"
          onClick={() => setShowDeactivated((v) => !v)}
          className="text-xs text-indigo-600 hover:underline"
        >
          {showDeactivated
            ? "Hide deactivated"
            : `Show ${deactivatedCount} deactivated`}
        </button>
      )}

      {/* List */}
      {isLoading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-24 rounded-lg" />
          ))}
        </div>
      ) : visible.length > 0 ? (
        <div className="space-y-4">
          {visible.map((item) => (
            <AdoptionCard
              key={item.adoption_id}
              item={item}
              isAdmin={isAdmin}
              onToggle={(i) => toggleMutation.mutate({ item: i })}
              toggling={togglingId === item.adoption_id}
            />
          ))}
        </div>
      ) : (
        <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed border-gray-200 py-12 text-center">
          <CheckCircle2 className="h-8 w-8 text-gray-300" />
          <p className="text-sm text-gray-500 font-medium">No curricula adopted yet</p>
          <p className="text-xs text-gray-400 max-w-xs">
            Browse the platform catalog and add curricula to your library so teachers
            can import and customize content for their classes.
          </p>
          {isAdmin && (
            <LinkButton href="/school/catalog" size="sm" className="mt-2">
              <LayoutGrid className="mr-1.5 h-4 w-4" />
              Browse catalog
            </LinkButton>
          )}
        </div>
      )}
    </div>
  );
}
