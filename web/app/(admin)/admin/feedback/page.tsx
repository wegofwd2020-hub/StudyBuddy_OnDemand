"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { getFeedbackList, resolveFeedback } from "@/lib/api/admin";
import { useAdmin, hasPermission } from "@/lib/hooks/useAdmin";
import { ShieldOff, MessageSquare, Star } from "lucide-react";

function StarRating({ rating }: { rating: number }) {
  return (
    <span
      className="flex gap-0.5"
      role="img"
      aria-label={`${rating} out of 5 stars`}
    >
      {[1, 2, 3, 4, 5].map((n) => (
        <Star
          key={n}
          aria-hidden="true"
          className={`h-3.5 w-3.5 ${
            n <= rating
              ? "fill-yellow-400 text-yellow-400"
              : "fill-none text-gray-300 opacity-60"
          }`}
          strokeWidth={n <= rating ? 0 : 1.5}
        />
      ))}
    </span>
  );
}

export default function AdminFeedbackPage() {
  const admin = useAdmin();
  const qc = useQueryClient();
  const [showResolved, setShowResolved] = useState(false);
  const [page, setPage] = useState(1);

  const { data, isLoading } = useQuery({
    queryKey: ["admin", "feedback", page, showResolved],
    queryFn: () => getFeedbackList(page, 20, showResolved ? true : false),
    staleTime: 30_000,
  });

  if (admin && !hasPermission(admin.role, "product_admin")) {
    return (
      <div className="mx-auto max-w-lg p-8">
        <div className="mb-2 flex items-center gap-3 text-red-600">
          <ShieldOff className="h-5 w-5" />
          <span className="font-semibold">Access denied</span>
        </div>
        <p className="text-sm text-gray-500">
          Viewing feedback requires <strong>product_admin</strong> or higher.
        </p>
      </div>
    );
  }

  async function handleResolve(feedbackId: string) {
    await resolveFeedback(feedbackId);
    qc.invalidateQueries({ queryKey: ["admin", "feedback"] });
  }

  return (
    <div className="mx-auto max-w-5xl p-8">
      <h1 className="mb-1 text-2xl font-bold text-gray-900">Student Feedback</h1>
      <p className="mb-6 text-sm text-gray-500">
        Ratings and comments submitted by students.
      </p>

      {/* Filter */}
      <div className="mb-6 flex gap-2">
        <button
          onClick={() => {
            setShowResolved(false);
            setPage(1);
          }}
          className={`rounded-full px-3 py-1.5 text-sm font-medium transition-colors ${
            !showResolved
              ? "bg-indigo-600 text-white"
              : "bg-gray-100 text-gray-600 hover:bg-gray-200"
          }`}
        >
          Open
        </button>
        <button
          onClick={() => {
            setShowResolved(true);
            setPage(1);
          }}
          className={`rounded-full px-3 py-1.5 text-sm font-medium transition-colors ${
            showResolved
              ? "bg-indigo-600 text-white"
              : "bg-gray-100 text-gray-600 hover:bg-gray-200"
          }`}
        >
          Resolved
        </button>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-20 animate-pulse rounded-xl bg-gray-100" />
          ))}
        </div>
      ) : data && data.items?.length > 0 ? (
        <>
          <p className="mb-3 text-xs text-gray-400">
            {data.total} item{data.total !== 1 ? "s" : ""}
          </p>
          <div className="space-y-3">
            {data.items.map((fb) => (
              <div
                key={fb.feedback_id}
                className="flex gap-4 rounded-xl border border-gray-200 bg-white p-4"
              >
                <div className="min-w-0 flex-1">
                  <div className="mb-1 flex items-center gap-3">
                    <span className="truncate text-sm font-medium text-gray-900">
                      {fb.unit_title}
                    </span>
                    <StarRating rating={fb.rating} />
                  </div>
                  {fb.comment && (
                    <p className="line-clamp-2 text-sm text-gray-600">{fb.comment}</p>
                  )}
                  <p className="mt-1 text-xs text-gray-400">
                    {new Date(fb.submitted_at).toLocaleString()}
                  </p>
                </div>
                {!fb.resolved && (
                  <button
                    onClick={() => handleResolve(fb.feedback_id)}
                    className="shrink-0 rounded-lg bg-gray-100 px-3 py-1.5 text-xs font-medium text-gray-600 transition-colors hover:bg-gray-200"
                  >
                    Resolve
                  </button>
                )}
              </div>
            ))}
          </div>

          {/* Pagination */}
          <div className="mt-6 flex items-center gap-3">
            <button
              disabled={page === 1}
              onClick={() => setPage(page - 1)}
              className="rounded-lg bg-gray-100 px-3 py-1.5 text-sm text-gray-600 transition-colors hover:bg-gray-200 disabled:opacity-40"
            >
              Previous
            </button>
            <span className="text-sm text-gray-500">Page {page}</span>
            <button
              disabled={(data.items?.length ?? 0) < 20}
              onClick={() => setPage(page + 1)}
              className="rounded-lg bg-gray-100 px-3 py-1.5 text-sm text-gray-600 transition-colors hover:bg-gray-200 disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </>
      ) : (
        <div className="py-16 text-center text-gray-400">
          <MessageSquare className="mx-auto mb-3 h-10 w-10 opacity-40" />
          <p className="text-sm">No {showResolved ? "resolved" : "open"} feedback.</p>
        </div>
      )}
    </div>
  );
}
