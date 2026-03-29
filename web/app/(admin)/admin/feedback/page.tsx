"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { getFeedbackList, resolveFeedback } from "@/lib/api/admin";
import { useAdmin, hasPermission } from "@/lib/hooks/useAdmin";
import { ShieldOff, MessageSquare, Star } from "lucide-react";

function StarRating({ rating }: { rating: number }) {
  return (
    <span className="flex gap-0.5">
      {[1, 2, 3, 4, 5].map((n) => (
        <Star
          key={n}
          className={`h-3.5 w-3.5 ${n <= rating ? "fill-yellow-400 text-yellow-400" : "text-gray-200"}`}
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
      <div className="p-8 max-w-lg mx-auto">
        <div className="flex items-center gap-3 text-red-600 mb-2">
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
    <div className="p-8 max-w-5xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-1">Student Feedback</h1>
      <p className="text-sm text-gray-500 mb-6">Ratings and comments submitted by students.</p>

      {/* Filter */}
      <div className="flex gap-2 mb-6">
        <button
          onClick={() => { setShowResolved(false); setPage(1); }}
          className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
            !showResolved ? "bg-indigo-600 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
          }`}
        >
          Open
        </button>
        <button
          onClick={() => { setShowResolved(true); setPage(1); }}
          className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
            showResolved ? "bg-indigo-600 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
          }`}
        >
          Resolved
        </button>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-20 bg-gray-100 rounded-xl animate-pulse" />
          ))}
        </div>
      ) : data && data.items?.length > 0 ? (
        <>
          <p className="text-xs text-gray-400 mb-3">
            {data.total} item{data.total !== 1 ? "s" : ""}
          </p>
          <div className="space-y-3">
            {data.items.map((fb) => (
              <div
                key={fb.feedback_id}
                className="bg-white rounded-xl border border-gray-200 p-4 flex gap-4"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3 mb-1">
                    <span className="text-sm font-medium text-gray-900 truncate">
                      {fb.unit_title}
                    </span>
                    <StarRating rating={fb.rating} />
                  </div>
                  {fb.comment && (
                    <p className="text-sm text-gray-600 line-clamp-2">{fb.comment}</p>
                  )}
                  <p className="text-xs text-gray-400 mt-1">
                    {new Date(fb.submitted_at).toLocaleString()}
                  </p>
                </div>
                {!fb.resolved && (
                  <button
                    onClick={() => handleResolve(fb.feedback_id)}
                    className="shrink-0 px-3 py-1.5 text-xs font-medium text-gray-600 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
                  >
                    Resolve
                  </button>
                )}
              </div>
            ))}
          </div>

          {/* Pagination */}
          <div className="flex items-center gap-3 mt-6">
            <button
              disabled={page === 1}
              onClick={() => setPage(page - 1)}
              className="px-3 py-1.5 text-sm text-gray-600 bg-gray-100 hover:bg-gray-200 disabled:opacity-40 rounded-lg transition-colors"
            >
              Previous
            </button>
            <span className="text-sm text-gray-500">Page {page}</span>
            <button
              disabled={(data.items?.length ?? 0) < 20}
              onClick={() => setPage(page + 1)}
              className="px-3 py-1.5 text-sm text-gray-600 bg-gray-100 hover:bg-gray-200 disabled:opacity-40 rounded-lg transition-colors"
            >
              Next
            </button>
          </div>
        </>
      ) : (
        <div className="text-center py-16 text-gray-400">
          <MessageSquare className="h-10 w-10 mx-auto mb-3 opacity-40" />
          <p className="text-sm">No {showResolved ? "resolved" : "open"} feedback.</p>
        </div>
      )}
    </div>
  );
}
