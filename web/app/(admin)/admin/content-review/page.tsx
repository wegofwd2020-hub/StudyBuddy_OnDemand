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
    <div className="p-8 max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-1">Content Review Queue</h1>
      <p className="text-sm text-gray-500 mb-6">Review, approve, and publish AI-generated content.</p>

      {/* Filter tabs */}
      <div className="flex gap-2 mb-6 flex-wrap">
        {(["pending", "approved", "published", "rejected", "blocked", ""] as StatusFilter[]).map(
          (s) => (
            <button
              key={s || "all"}
              onClick={() => setStatusFilter(s)}
              className={cn(
                "px-3 py-1.5 rounded-full text-sm font-medium transition-colors",
                statusFilter === s
                  ? "bg-indigo-600 text-white"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200",
              )}
            >
              {s || "All"}
            </button>
          ),
        )}
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-14 bg-gray-100 rounded-xl animate-pulse" />
          ))}
        </div>
      ) : data && data.items.length > 0 ? (
        <>
          <p className="text-xs text-gray-400 mb-3">{data.total} item{data.total !== 1 ? "s" : ""}</p>
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Unit</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Grade</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Lang</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Status</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Submitted</th>
                  <th className="text-right px-4 py-3 font-medium text-gray-600"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {data.items.map((item) => (
                  <tr key={item.version_id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium text-gray-900">
                      {item.unit_title}
                    </td>
                    <td className="px-4 py-3 text-gray-600">Gr. {item.grade}</td>
                    <td className="px-4 py-3 text-gray-600 uppercase font-mono text-xs">
                      {item.lang}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={cn(
                          "inline-flex items-center px-2 py-0.5 rounded text-xs font-medium",
                          STATUS_STYLES[item.status] ?? "bg-gray-100 text-gray-600",
                        )}
                      >
                        {item.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-500 text-xs">
                      {new Date(item.submitted_at).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Link
                        href={`/admin/content-review/${item.version_id}`}
                        className="text-xs text-indigo-600 hover:underline"
                      >
                        Review →
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : (
        <div className="text-center py-16 text-gray-400">
          <ClipboardList className="h-10 w-10 mx-auto mb-3 opacity-40" />
          <p className="text-sm">
            No {statusFilter || ""} items in the queue.
          </p>
        </div>
      )}
    </div>
  );
}
