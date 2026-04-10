"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { batchApproveGrade, getReviewQueue } from "@/lib/api/admin";
import { useAdmin } from "@/lib/hooks/useAdmin";
import { cn } from "@/lib/utils";
import { AlertTriangle, CheckCheck, ClipboardList, UserCheck } from "lucide-react";

type StatusFilter = "pending" | "approved" | "published" | "rejected" | "blocked" | "";

const STATUS_STYLES: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-700",
  ready_for_review: "bg-yellow-100 text-yellow-700",
  needs_review: "bg-amber-100 text-amber-700",
  approved: "bg-blue-100 text-blue-700",
  published: "bg-green-100 text-green-700",
  rejected: "bg-red-100 text-red-700",
  blocked: "bg-gray-200 text-gray-700",
};

/** Extract a display label from curriculum_id, e.g. "default-2026-g8" → "Grade 8 (2026)" */
function gradeLabel(curriculumId: string): string {
  const m = curriculumId.match(/g(\d+)/i);
  const y = curriculumId.match(/(\d{4})/);
  if (m) {
    return y ? `Grade ${m[1]} (${y[1]})` : `Grade ${m[1]}`;
  }
  return curriculumId;
}

interface ConfirmState {
  curriculumId: string;
  pendingCount: number;
}

export default function AdminContentReviewPage() {
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("pending");
  const [myAssignments, setMyAssignments] = useState(false);
  const [confirm, setConfirm] = useState<ConfirmState | null>(null);
  const queryClient = useQueryClient();
  const admin = useAdmin();

  const { data, isLoading } = useQuery({
    queryKey: [
      "admin",
      "content-review",
      statusFilter,
      myAssignments ? admin?.admin_id : null,
    ],
    queryFn: () =>
      getReviewQueue(
        statusFilter || undefined,
        undefined,
        undefined,
        myAssignments && admin ? admin.admin_id : undefined,
      ),
    staleTime: 30_000,
  });

  const batchMutation = useMutation({
    mutationFn: (curriculumId: string) => batchApproveGrade(curriculumId),
    onSuccess: () => {
      setConfirm(null);
      void queryClient.invalidateQueries({ queryKey: ["admin", "content-review"] });
    },
  });

  // Group items by curriculum_id, preserving insertion order
  const groups: Map<string, NonNullable<typeof data>["items"]> = new Map();
  if (data) {
    for (const item of data.items) {
      const key = item.curriculum_id;
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key)!.push(item);
    }
  }

  return (
    <div className="mx-auto max-w-6xl p-8">
      <h1 className="mb-1 text-2xl font-bold text-gray-900">Content Review Queue</h1>
      <p className="mb-6 text-sm text-gray-500">
        Review, approve, and publish AI-generated content.
      </p>

      {/* Filter bar */}
      <div className="mb-6 flex flex-wrap items-center gap-2">
        {(
          [
            "pending",
            "approved",
            "published",
            "rejected",
            "blocked",
            "",
          ] as StatusFilter[]
        ).map((s) => (
          <button
            key={s || "all"}
            onClick={() => setStatusFilter(s)}
            className={cn(
              "rounded-full px-3 py-1.5 text-sm font-medium transition-colors",
              statusFilter === s
                ? "bg-indigo-600 text-white"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200",
            )}
          >
            {s || "All"}
          </button>
        ))}
        <div className="ml-auto">
          <button
            onClick={() => setMyAssignments((v) => !v)}
            className={cn(
              "flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-medium transition-colors",
              myAssignments
                ? "bg-indigo-100 text-indigo-700"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200",
            )}
          >
            <UserCheck className="h-3.5 w-3.5" />
            My assignments
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-14 animate-pulse rounded-xl bg-gray-100" />
          ))}
        </div>
      ) : data && data.items.length > 0 ? (
        <>
          <p className="mb-3 text-xs text-gray-400">
            {data.total} item{data.total !== 1 ? "s" : ""}
          </p>
          <div className="space-y-6">
            {Array.from(groups.entries()).map(([curriculumId, items]) => {
              const pendingCount = items.filter((i) => i.status === "pending").length;
              const showBatchApprove = statusFilter === "pending" && pendingCount > 0;

              return (
                <div key={curriculumId}>
                  {/* Grade group header */}
                  <div className="mb-2 flex items-center justify-between">
                    <h2 className="text-sm font-semibold text-gray-700">
                      {gradeLabel(curriculumId)}
                      <span className="ml-2 font-mono text-xs font-normal text-gray-400">
                        {curriculumId}
                      </span>
                    </h2>
                    {showBatchApprove && (
                      <button
                        onClick={() => setConfirm({ curriculumId, pendingCount })}
                        className="flex items-center gap-1.5 rounded-lg bg-indigo-50 px-3 py-1.5 text-xs font-medium text-indigo-700 transition-colors hover:bg-indigo-100"
                      >
                        <CheckCheck className="h-3.5 w-3.5" />
                        Approve all pending ({pendingCount})
                      </button>
                    )}
                  </div>

                  <div className="overflow-hidden rounded-xl border border-gray-200 bg-white">
                    <table className="w-full text-sm">
                      <thead className="border-b border-gray-200 bg-gray-50">
                        <tr>
                          <th className="px-4 py-3 text-left font-medium text-gray-600">
                            Subject
                          </th>
                          <th className="px-4 py-3 text-left font-medium text-gray-600">
                            Lang
                          </th>
                          <th className="px-4 py-3 text-left font-medium text-gray-600">
                            Status
                          </th>
                          <th className="px-4 py-3 text-left font-medium text-gray-600">
                            Submitted
                          </th>
                          <th className="px-4 py-3 text-left font-medium text-gray-600">
                            Assigned to
                          </th>
                          <th className="px-4 py-3 text-right font-medium text-gray-600"></th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {items.map((item) => (
                          <tr key={item.version_id} className="hover:bg-gray-50">
                            <td className="px-4 py-3">
                              <div className="flex items-start gap-2">
                                <div className="min-w-0">
                                  <p className="font-medium text-gray-900">
                                    {item.subject_name ?? item.subject}
                                  </p>
                                  {item.subject_name && (
                                    <p className="font-mono text-xs text-gray-400">
                                      {item.subject}
                                    </p>
                                  )}
                                </div>
                                {item.alex_warnings_count > 0 && (
                                  <span
                                    title={`${item.alex_warnings_count} unreviewed AlexJS warning${item.alex_warnings_count !== 1 ? "s" : ""} — must acknowledge before approving`}
                                    className="mt-0.5 inline-flex flex-shrink-0 items-center gap-1 rounded bg-red-100 px-1.5 py-0.5 text-xs font-semibold text-red-700"
                                  >
                                    <AlertTriangle className="h-3 w-3" />
                                    {item.alex_warnings_count}
                                  </span>
                                )}
                              </div>
                            </td>
                            <td className="px-4 py-3 text-xs text-gray-500">
                              v{item.version_number}
                            </td>
                            <td className="px-4 py-3">
                              <span
                                className={cn(
                                  "inline-flex items-center rounded px-2 py-0.5 text-xs font-medium",
                                  STATUS_STYLES[item.status] ??
                                    "bg-gray-100 text-gray-600",
                                )}
                              >
                                {item.status}
                              </span>
                            </td>
                            <td className="px-4 py-3 text-xs text-gray-500">
                              {new Date(item.generated_at).toLocaleDateString()}
                            </td>
                            <td className="px-4 py-3 text-xs text-gray-500">
                              {item.assigned_to_email ?? (
                                <span className="text-gray-300">—</span>
                              )}
                            </td>
                            <td className="px-4 py-3 text-right">
                              {item.has_content ? (
                                <Link
                                  href={`/admin/content-review/${item.version_id}`}
                                  className="text-xs text-indigo-600 hover:underline"
                                >
                                  Review →
                                </Link>
                              ) : (
                                <span className="inline-flex items-center gap-1 rounded bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-400">
                                  No content
                                </span>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              );
            })}
          </div>
        </>
      ) : (
        <div className="py-16 text-center text-gray-400">
          <ClipboardList className="mx-auto mb-3 h-10 w-10 opacity-40" />
          <p className="text-sm">No {statusFilter || ""} items in the queue.</p>
        </div>
      )}

      {/* Batch approve confirmation dialog */}
      {confirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
            <h2 className="mb-2 text-lg font-semibold text-gray-900">
              Approve all pending?
            </h2>
            <p className="mb-1 text-sm text-gray-600">
              This will approve{" "}
              <span className="font-semibold">{confirm.pendingCount}</span> pending
              subject
              {confirm.pendingCount !== 1 ? "s" : ""} for{" "}
              <span className="font-mono text-xs">{confirm.curriculumId}</span>.
            </p>
            <p className="mb-6 text-xs text-gray-400">
              Each subject will be recorded individually in the review history.
            </p>
            {batchMutation.isError && (
              <p className="mb-4 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-600">
                Something went wrong. Please try again.
              </p>
            )}
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setConfirm(null)}
                disabled={batchMutation.isPending}
                className="rounded-lg border border-gray-200 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={() => batchMutation.mutate(confirm.curriculumId)}
                disabled={batchMutation.isPending}
                className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
              >
                {batchMutation.isPending ? "Approving…" : "Approve all"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
