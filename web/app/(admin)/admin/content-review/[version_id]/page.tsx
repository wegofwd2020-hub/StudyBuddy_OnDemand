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
import {
  ArrowLeft,
  CheckCircle,
  XCircle,
  Globe,
  RotateCcw,
  ShieldOff,
} from "lucide-react";

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
    <div className="mx-auto max-w-3xl p-8">
      <Link
        href="/admin/content-review"
        className="mb-6 inline-flex items-center gap-1.5 text-sm text-gray-500 transition-colors hover:text-gray-900"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to queue
      </Link>

      {isLoading ? (
        <div className="space-y-4">
          <div className="h-8 animate-pulse rounded-lg bg-gray-100" />
          <div className="h-48 animate-pulse rounded-xl bg-gray-100" />
        </div>
      ) : item ? (
        <div className="space-y-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{item.unit_title}</h1>
            <p className="mt-1 text-sm text-gray-500">
              Grade {item.grade} · {item.subject} ·{" "}
              <span className="font-mono uppercase">{item.lang}</span> · v
              {item.content_version}
            </p>
          </div>

          {/* Meta */}
          <div className="flex flex-wrap gap-3 text-xs text-gray-500">
            <span>
              Status: <strong className="text-gray-900">{item.status}</strong>
            </span>
            <span>
              Quiz questions: <strong className="text-gray-900">{item.quiz_count}</strong>
            </span>
            {item.alexjs_score !== null && (
              <span>
                AlexJS score:{" "}
                <strong className="text-gray-900">{item.alexjs_score}</strong>
              </span>
            )}
            <span>Submitted: {new Date(item.submitted_at).toLocaleString()}</span>
          </div>

          {/* Lesson preview */}
          <div className="rounded-xl border border-gray-200 bg-gray-50 p-5">
            <h2 className="mb-3 text-sm font-semibold text-gray-700">Lesson Preview</h2>
            <p className="text-sm leading-relaxed whitespace-pre-wrap text-gray-700">
              {item.lesson_preview}
            </p>
          </div>

          {/* Annotations */}
          {item.annotations.length > 0 && (
            <div>
              <h2 className="mb-2 text-sm font-semibold text-gray-700">Annotations</h2>
              <div className="space-y-2">
                {item.annotations.map((ann, i) => (
                  <div
                    key={i}
                    className="rounded-lg border border-yellow-200 bg-yellow-50 p-3 text-sm"
                  >
                    <p className="text-gray-700">{ann.note}</p>
                    <p className="mt-1 text-xs text-gray-400">
                      {ann.reviewer_id} · {new Date(ann.created_at).toLocaleString()}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
              {error}
            </div>
          )}

          {/* Actions */}
          {item.status === "pending" && (
            <div className="flex flex-wrap gap-3 pt-2">
              <button
                disabled={acting}
                onClick={() => performAction(() => approveReview(version_id))}
                className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-500 disabled:opacity-50"
              >
                <CheckCircle className="h-4 w-4" />
                Approve
              </button>
              <button
                disabled={acting}
                onClick={() => setModal("reject")}
                className="flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-red-500 disabled:opacity-50"
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
                className="flex items-center gap-2 rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-green-500 disabled:opacity-50"
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
                className="flex items-center gap-2 rounded-lg bg-yellow-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-yellow-500 disabled:opacity-50"
              >
                <RotateCcw className="h-4 w-4" />
                Rollback
              </button>
              {canBlock && (
                <button
                  disabled={acting}
                  onClick={() => setModal("block")}
                  className="flex items-center gap-2 rounded-lg bg-gray-700 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-gray-600 disabled:opacity-50"
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
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-md rounded-xl border border-gray-200 bg-white p-6">
            <h2 className="mb-4 text-base font-semibold text-gray-900 capitalize">
              {modal} content
            </h2>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder={`Reason for ${modal}…`}
              rows={3}
              className="w-full resize-none rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
            />
            <div className="mt-4 flex gap-3">
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
                  "flex-1 rounded-lg py-2 text-sm font-medium text-white transition-colors disabled:opacity-50",
                  modal === "reject"
                    ? "bg-red-600 hover:bg-red-500"
                    : "bg-gray-700 hover:bg-gray-600",
                )}
              >
                Confirm {modal}
              </button>
              <button
                onClick={() => {
                  setModal(null);
                  setReason("");
                }}
                className="flex-1 py-2 text-sm text-gray-600 transition-colors hover:text-gray-900"
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
