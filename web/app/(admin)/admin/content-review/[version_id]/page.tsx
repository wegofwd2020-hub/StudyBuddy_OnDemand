"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getReviewItem,
  approveReview,
  rejectReview,
  publishReview,
  rollbackReview,
  blockReview,
} from "@/lib/api/admin";
import { useAdmin, hasPermission } from "@/lib/hooks/useAdmin";
import { cn } from "@/lib/utils";
import { ArrowLeft, CheckCircle, XCircle, Globe, RotateCcw, ShieldOff } from "lucide-react";

type ActionModal = "reject" | "block" | null;

export default function AdminContentReviewDetailPage() {
  const { version_id } = useParams<{ version_id: string }>();
  const router = useRouter();
  const qc = useQueryClient();
  const admin = useAdmin();

  const [modal, setModal] = useState<ActionModal>(null);
  const [reason, setReason] = useState("");
  const [acting, setActing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { data: item, isLoading } = useQuery({
    queryKey: ["admin", "content-review", version_id],
    queryFn: () => getReviewItem(version_id),
    staleTime: 60_000,
  });

  async function performAction(action: () => Promise<void>) {
    setActing(true);
    setError(null);
    try {
      await action();
      qc.invalidateQueries({ queryKey: ["admin", "content-review"] });
      router.push("/admin/content-review");
    } catch {
      setError("Action failed. Please try again.");
    } finally {
      setActing(false);
    }
  }

  const canPublish = admin && hasPermission(admin.role, "product_admin");
  const canBlock = canPublish;

  return (
    <div className="p-8 max-w-3xl mx-auto">
      <Link
        href="/admin/content-review"
        className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-900 mb-6 transition-colors"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to queue
      </Link>

      {isLoading ? (
        <div className="space-y-4">
          <div className="h-8 bg-gray-100 rounded-lg animate-pulse" />
          <div className="h-48 bg-gray-100 rounded-xl animate-pulse" />
        </div>
      ) : item ? (
        <div className="space-y-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{item.unit_title}</h1>
            <p className="text-sm text-gray-500 mt-1">
              Grade {item.grade} · {item.subject} · <span className="uppercase font-mono">{item.lang}</span> ·
              v{item.content_version}
            </p>
          </div>

          {/* Meta */}
          <div className="flex flex-wrap gap-3 text-xs text-gray-500">
            <span>Status: <strong className="text-gray-900">{item.status}</strong></span>
            <span>Quiz questions: <strong className="text-gray-900">{item.quiz_count}</strong></span>
            {item.alexjs_score !== null && (
              <span>AlexJS score: <strong className="text-gray-900">{item.alexjs_score}</strong></span>
            )}
            <span>Submitted: {new Date(item.submitted_at).toLocaleString()}</span>
          </div>

          {/* Lesson preview */}
          <div className="bg-gray-50 rounded-xl border border-gray-200 p-5">
            <h2 className="text-sm font-semibold text-gray-700 mb-3">Lesson Preview</h2>
            <p className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">
              {item.lesson_preview}
            </p>
          </div>

          {/* Annotations */}
          {item.annotations.length > 0 && (
            <div>
              <h2 className="text-sm font-semibold text-gray-700 mb-2">Annotations</h2>
              <div className="space-y-2">
                {item.annotations.map((ann, i) => (
                  <div key={i} className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 text-sm">
                    <p className="text-gray-700">{ann.note}</p>
                    <p className="text-xs text-gray-400 mt-1">
                      {ann.reviewer_id} · {new Date(ann.created_at).toLocaleString()}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
              {error}
            </div>
          )}

          {/* Actions */}
          {item.status === "pending" && (
            <div className="flex flex-wrap gap-3 pt-2">
              <button
                disabled={acting}
                onClick={() => performAction(() => approveReview(version_id))}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors"
              >
                <CheckCircle className="h-4 w-4" />
                Approve
              </button>
              <button
                disabled={acting}
                onClick={() => setModal("reject")}
                className="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-500 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors"
              >
                <XCircle className="h-4 w-4" />
                Reject
              </button>
            </div>
          )}

          {item.status === "approved" && canPublish && (
            <div className="flex flex-wrap gap-3 pt-2">
              <button
                disabled={acting}
                onClick={() => performAction(() => publishReview(version_id))}
                className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-500 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors"
              >
                <Globe className="h-4 w-4" />
                Publish
              </button>
            </div>
          )}

          {item.status === "published" && canPublish && (
            <div className="flex flex-wrap gap-3 pt-2">
              <button
                disabled={acting}
                onClick={() => performAction(() => rollbackReview(version_id))}
                className="flex items-center gap-2 px-4 py-2 bg-yellow-600 hover:bg-yellow-500 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors"
              >
                <RotateCcw className="h-4 w-4" />
                Rollback
              </button>
              {canBlock && (
                <button
                  disabled={acting}
                  onClick={() => setModal("block")}
                  className="flex items-center gap-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors"
                >
                  <ShieldOff className="h-4 w-4" />
                  Block
                </button>
              )}
            </div>
          )}
        </div>
      ) : (
        <p className="text-sm text-gray-400">Content version not found.</p>
      )}

      {/* Reason modal (reject or block) */}
      {modal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl border border-gray-200 p-6 w-full max-w-md">
            <h2 className="text-base font-semibold text-gray-900 mb-4 capitalize">
              {modal} content
            </h2>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder={`Reason for ${modal}…`}
              rows={3}
              className="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
            />
            <div className="flex gap-3 mt-4">
              <button
                disabled={acting || !reason.trim()}
                onClick={() => {
                  const action =
                    modal === "reject"
                      ? () => rejectReview(version_id, reason)
                      : () => blockReview(version_id, reason);
                  setModal(null);
                  setReason("");
                  performAction(action);
                }}
                className={cn(
                  "flex-1 py-2 text-sm font-medium text-white rounded-lg transition-colors disabled:opacity-50",
                  modal === "reject"
                    ? "bg-red-600 hover:bg-red-500"
                    : "bg-gray-700 hover:bg-gray-600",
                )}
              >
                Confirm {modal}
              </button>
              <button
                onClick={() => { setModal(null); setReason(""); }}
                className="flex-1 py-2 text-sm text-gray-600 hover:text-gray-900 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
