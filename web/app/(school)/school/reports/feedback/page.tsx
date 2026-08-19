"use client";

import { useState } from "react";
import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { useTeacher } from "@/lib/hooks/useTeacher";
import { getFeedbackReport } from "@/lib/api/reports";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { MessageSquare } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * Student feedback, as a paginated table.
 *
 * This was a card per unit containing every item ever recorded, which was fine
 * at five rows and unusable at five hundred (#611). The backend now paginates,
 * so the page shows one row per item, newest first, with the filters the API
 * already supported but the UI never exposed.
 */

const PAGE_SIZE = 25;

type ReviewedFilter = "all" | "unreviewed" | "reviewed";
type VerdictFilter = "all" | "helpful" | "not_helpful";

function Verdict({
  helpful,
  rating,
}: {
  helpful: boolean | null;
  rating: number | null;
}) {
  if (typeof helpful === "boolean") {
    return (
      <span
        className={cn(
          "text-sm font-medium whitespace-nowrap",
          helpful ? "text-emerald-600" : "text-rose-600",
        )}
      >
        {helpful ? "👍 Helpful" : "👎 Not helpful"}
      </span>
    );
  }
  if (rating !== null) return <span className="text-sm text-gray-700">{rating} / 5</span>;
  return <span className="text-sm text-gray-300">—</span>;
}

export default function FeedbackReportPage() {
  const teacher = useTeacher();
  const schoolId = teacher?.school_id ?? "";

  const [page, setPage] = useState(1);
  const [reviewedFilter, setReviewedFilter] = useState<ReviewedFilter>("all");
  const [verdictFilter, setVerdictFilter] = useState<VerdictFilter>("all");

  const reviewed =
    reviewedFilter === "all" ? undefined : reviewedFilter === "reviewed" ? true : false;

  const { data, isLoading } = useQuery({
    queryKey: ["school", "reports", "feedback", schoolId, page, reviewed],
    queryFn: () => getFeedbackReport(schoolId, { page, pageSize: PAGE_SIZE, reviewed }),
    enabled: Boolean(schoolId),
    // Keep the previous page visible while the next one loads, so paging does
    // not flash an empty table.
    placeholderData: keepPreviousData,
  });

  // The verdict split is not a server-side filter, so it narrows the current
  // page only — labelled as such below rather than pretending otherwise.
  const rows = (data?.items ?? []).filter((item) => {
    if (verdictFilter === "helpful") return item.helpful === true;
    if (verdictFilter === "not_helpful") return item.helpful === false;
    return true;
  });

  const total = data?.pagination.total ?? 0;
  const lastPage = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="space-y-6 p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold text-gray-900">Student Feedback</h1>
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <span>{data?.total_feedback_count ?? 0} total</span>
          {(data?.unreviewed_count ?? 0) > 0 && (
            <Badge variant="secondary">{data?.unreviewed_count} unreviewed</Badge>
          )}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {(["all", "unreviewed", "reviewed"] as const).map((value) => (
          <button
            key={value}
            onClick={() => {
              setReviewedFilter(value);
              setPage(1);
            }}
            className={cn(
              "rounded-full px-3 py-1 text-xs font-medium",
              reviewedFilter === value
                ? "bg-gray-900 text-white"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200",
            )}
          >
            {value === "all" ? "All" : value === "unreviewed" ? "Unreviewed" : "Reviewed"}
          </button>
        ))}
        <span className="mx-1 h-4 w-px bg-gray-200" aria-hidden="true" />
        {(["all", "helpful", "not_helpful"] as const).map((value) => (
          <button
            key={value}
            onClick={() => setVerdictFilter(value)}
            className={cn(
              "rounded-full px-3 py-1 text-xs font-medium",
              verdictFilter === value
                ? "bg-gray-900 text-white"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200",
            )}
          >
            {value === "all"
              ? "Any verdict"
              : value === "helpful"
                ? "Helpful"
                : "Not helpful"}
          </button>
        ))}
        {verdictFilter !== "all" && (
          <span className="text-xs text-gray-400">filters this page only</span>
        )}
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <MessageSquare className="h-4 w-4 text-gray-500" aria-hidden="true" />
            Feedback
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : rows.length === 0 ? (
            <p className="py-8 text-center text-sm text-gray-500">No feedback to show.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-gray-200 text-xs tracking-wide text-gray-500 uppercase">
                  <tr>
                    <th scope="col" className="px-3 py-2">
                      Unit
                    </th>
                    <th scope="col" className="px-3 py-2">
                      Verdict
                    </th>
                    <th scope="col" className="px-3 py-2">
                      Comment
                    </th>
                    <th scope="col" className="px-3 py-2">
                      Type
                    </th>
                    <th scope="col" className="px-3 py-2">
                      Date
                    </th>
                    <th scope="col" className="px-3 py-2">
                      Status
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {rows.map((item) => (
                    <tr key={item.feedback_id} className="hover:bg-gray-50">
                      <td className="px-3 py-2 font-medium text-gray-900">
                        {item.unit_name ?? item.unit_id ?? "—"}
                      </td>
                      <td className="px-3 py-2">
                        <Verdict helpful={item.helpful} rating={item.rating} />
                      </td>
                      <td className="max-w-md px-3 py-2 text-gray-700">
                        {item.message ?? <span className="text-gray-300">—</span>}
                      </td>
                      <td className="px-3 py-2 text-gray-500 capitalize">
                        {item.content_type ?? item.category}
                      </td>
                      <td className="px-3 py-2 whitespace-nowrap text-gray-500">
                        {new Date(item.submitted_at).toLocaleDateString()}
                      </td>
                      <td className="px-3 py-2">
                        {item.reviewed ? (
                          <span className="text-xs text-gray-400">Reviewed</span>
                        ) : (
                          <Badge variant="secondary">Unreviewed</Badge>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {total > PAGE_SIZE && (
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-500">
            Page {page} of {lastPage} · {total} items
          </span>
          <div className="flex gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="rounded-lg border border-gray-200 px-3 py-1 disabled:opacity-40"
            >
              Previous
            </button>
            <button
              onClick={() => setPage((p) => Math.min(lastPage, p + 1))}
              disabled={page >= lastPage}
              className="rounded-lg border border-gray-200 px-3 py-1 disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
