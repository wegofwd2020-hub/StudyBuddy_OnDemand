"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { getReviewQueue } from "@/lib/api/admin";
import { cn } from "@/lib/utils";
import { ClipboardList } from "lucide-react";

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

export default function AdminContentReviewPage() {
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("pending");

  const { data, isLoading } = useQuery({
    queryKey: ["admin", "content-review", statusFilter],
    queryFn: () => getReviewQueue(statusFilter || undefined),
    staleTime: 30_000,
  });

  return (
    <div className="mx-auto max-w-6xl p-8">
      <h1 className="mb-1 text-2xl font-bold text-gray-900">Content Review Queue</h1>
      <p className="mb-6 text-sm text-gray-500">
        Review, approve, and publish AI-generated content.
      </p>

      {/* Filter tabs */}
      <div className="mb-6 flex flex-wrap gap-2">
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
          <div className="overflow-hidden rounded-xl border border-gray-200 bg-white">
            <table className="w-full text-sm">
              <thead className="border-b border-gray-200 bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Unit</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Grade</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Lang</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">
                    Status
                  </th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">
                    Submitted
                  </th>
                  <th className="px-4 py-3 text-right font-medium text-gray-600"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {data.items.map((item) => (
                  <tr key={item.version_id} className="hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <p className="font-medium text-gray-900">
                        {item.subject_name ?? item.subject}
                      </p>
                      {item.subject_name && (
                        <p className="font-mono text-xs text-gray-400">{item.subject}</p>
                      )}
                    </td>
                    <td className="px-4 py-3 text-gray-600">{item.curriculum_id}</td>
                    <td className="px-4 py-3 text-xs text-gray-500">
                      v{item.version_number}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={cn(
                          "inline-flex items-center rounded px-2 py-0.5 text-xs font-medium",
                          STATUS_STYLES[item.status] ?? "bg-gray-100 text-gray-600",
                        )}
                      >
                        {item.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-500">
                      {new Date(item.generated_at).toLocaleDateString()}
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
        </>
      ) : (
        <div className="py-16 text-center text-gray-400">
          <ClipboardList className="mx-auto mb-3 h-10 w-10 opacity-40" />
          <p className="text-sm">No {statusFilter || ""} items in the queue.</p>
        </div>
      )}
    </div>
  );
}
