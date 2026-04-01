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
  blockVersionContent,
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
  Clock,
  MessageSquare,
  GitCompare,
} from "lucide-react";

type ActionModal = "reject" | "block" | null;

const CONTENT_TYPES = ["lesson", "quiz", "tutorial", "experiment"] as const;

const STATUS_STYLES: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-700",
  ready_for_review: "bg-yellow-100 text-yellow-700",
  in_review: "bg-blue-100 text-blue-700",
  approved: "bg-blue-100 text-blue-700",
  published: "bg-green-100 text-green-700",
  rejected: "bg-red-100 text-red-700",
  blocked: "bg-gray-200 text-gray-700",
};

const ACTION_LABELS: Record<string, string> = {
  open: "Opened for review",
  approve: "Approved",
  reject: "Rejected",
  rate: "Rated",
  publish: "Published",
  rollback: "Rolled back",
};

export default function AdminContentReviewDetailPage() {
  const { version_id } = useParams<{ version_id: string }>();
  const router = useRouter();
  const qc = useQueryClient();
  const admin = useAdmin();

  const [modal, setModal] = useState<ActionModal>(null);
  const [reason, setReason] = useState("");
  const [blockUnit, setBlockUnit] = useState("");
  const [blockType, setBlockType] = useState<string>("lesson");
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
          {/* Header */}
          <div>
            <div className="flex items-start justify-between gap-4">
              <h1 className="text-2xl font-bold text-gray-900">{item.subject}</h1>
              <span
                className={cn(
                  "mt-1 inline-flex items-center rounded px-2.5 py-1 text-xs font-medium",
                  STATUS_STYLES[item.status] ?? "bg-gray-100 text-gray-600",
                )}
              >
                {item.status}
              </span>
            </div>
            <p className="mt-1 text-sm text-gray-500">
              {item.curriculum_id} · Version {item.version_number} ·{" "}
              {item.alex_warnings_count} AlexJS warning
              {item.alex_warnings_count !== 1 ? "s" : ""}
            </p>
            <p className="mt-0.5 text-xs text-gray-400">
              Generated {new Date(item.generated_at).toLocaleString()}
              {item.published_at && (
                <> · Published {new Date(item.published_at).toLocaleString()}</>
              )}
            </p>
            {item.version_number > 1 && (
              <Link
                href={`/admin/content-review/${version_id}/diff`}
                className="mt-2 inline-flex items-center gap-1.5 rounded-md border border-gray-200 bg-white px-3 py-1.5 text-xs font-medium text-gray-600 transition-colors hover:border-indigo-300 hover:text-indigo-700"
              >
                <GitCompare className="h-3.5 w-3.5" />
                Compare with previous version
              </Link>
            )}
          </div>

          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
              {error}
            </div>
          )}

          {/* Units in this subject version */}
          {item.units.length > 0 && (
            <div className="rounded-xl border border-gray-200 bg-white">
              <div className="border-b border-gray-100 px-4 py-3">
                <h2 className="text-sm font-semibold text-gray-700">
                  Units ({item.units.length})
                </h2>
              </div>
              <ul className="divide-y divide-gray-50">
                {item.units.map((u) => (
                  <li
                    key={u.unit_id}
                    className="flex items-center justify-between px-4 py-2.5"
                  >
                    <div>
                      <p className="text-sm font-medium text-gray-900">{u.title}</p>
                      <p className="font-mono text-xs text-gray-400">{u.unit_id}</p>
                    </div>
                    <Link
                      href={`/admin/content-review/${version_id}/unit/${u.unit_id}`}
                      className="ml-4 flex-shrink-0 rounded-md border border-gray-200 px-2.5 py-1 text-xs font-medium text-gray-600 transition-colors hover:border-indigo-300 hover:text-indigo-700"
                    >
                      View →
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Annotations */}
          {item.annotations.length > 0 && (
            <div>
              <h2 className="mb-2 flex items-center gap-1.5 text-sm font-semibold text-gray-700">
                <MessageSquare className="h-4 w-4" />
                Annotations ({item.annotations.length})
              </h2>
              <div className="space-y-2">
                {item.annotations.map((ann) => (
                  <div
                    key={ann.annotation_id}
                    className="rounded-lg border border-yellow-200 bg-yellow-50 p-3 text-sm"
                  >
                    <p className="text-xs font-medium text-gray-500">
                      {ann.unit_id} · {ann.content_type}
                    </p>
                    <p className="mt-1 text-gray-700">{ann.annotation_text}</p>
                    <p className="mt-1 text-xs text-gray-400">
                      {ann.reviewer_email ?? "admin"} ·{" "}
                      {new Date(ann.created_at).toLocaleString()}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Review history */}
          {item.review_history.length > 0 && (
            <div>
              <h2 className="mb-2 flex items-center gap-1.5 text-sm font-semibold text-gray-700">
                <Clock className="h-4 w-4" />
                Review history
              </h2>
              <div className="space-y-1.5">
                {item.review_history.map((h) => (
                  <div
                    key={h.review_id}
                    className="flex items-start gap-3 rounded-lg border border-gray-100 bg-gray-50 px-3 py-2 text-sm"
                  >
                    <span className="mt-0.5 min-w-[90px] font-medium text-gray-700">
                      {ACTION_LABELS[h.action] ?? h.action}
                    </span>
                    <span className="flex-1 text-gray-500">{h.notes ?? "—"}</span>
                    <span className="text-xs whitespace-nowrap text-gray-400">
                      {h.reviewer_email ?? "system"} ·{" "}
                      {new Date(h.reviewed_at).toLocaleString()}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="flex flex-wrap gap-3 border-t border-gray-100 pt-4">
            {item.status === "pending" && (
              <>
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
              </>
            )}

            {item.status === "approved" && canPublish && (
              <button
                disabled={acting}
                onClick={() => performAction(() => publishReview(version_id))}
                className="flex items-center gap-2 rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-green-500 disabled:opacity-50"
              >
                <Globe className="h-4 w-4" />
                Publish
              </button>
            )}

            {item.status === "published" && canPublish && (
              <button
                disabled={acting}
                onClick={() => performAction(() => rollbackReview(version_id))}
                className="flex items-center gap-2 rounded-lg bg-yellow-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-yellow-500 disabled:opacity-50"
              >
                <RotateCcw className="h-4 w-4" />
                Rollback
              </button>
            )}

            {canPublish && item.units.length > 0 && (
              <button
                disabled={acting}
                onClick={() => {
                  setBlockUnit(item.units[0].unit_id);
                  setBlockType("lesson");
                  setReason("");
                  setModal("block");
                }}
                className="flex items-center gap-2 rounded-lg bg-gray-700 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-gray-600 disabled:opacity-50"
              >
                <ShieldOff className="h-4 w-4" />
                Block unit content
              </button>
            )}
          </div>
        </div>
      ) : (
        <p className="text-sm text-gray-400">Content version not found.</p>
      )}

      {/* Modals */}
      {modal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-md rounded-xl border border-gray-200 bg-white p-6">
            {modal === "reject" ? (
              <>
                <h2 className="mb-4 text-base font-semibold text-gray-900">
                  Reject version
                </h2>
                <textarea
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  placeholder="Reason for rejection…"
                  rows={3}
                  className="w-full resize-none rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                />
                <div className="mt-4 flex gap-3">
                  <button
                    disabled={acting || !reason.trim()}
                    onClick={() => {
                      const r = reason;
                      setModal(null);
                      setReason("");
                      performAction(() => rejectReview(version_id, r));
                    }}
                    className="flex-1 rounded-lg bg-red-600 py-2 text-sm font-medium text-white transition-colors hover:bg-red-500 disabled:opacity-50"
                  >
                    Confirm reject
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
              </>
            ) : (
              <>
                <h2 className="mb-1 text-base font-semibold text-gray-900">
                  Block unit content
                </h2>
                <p className="mb-4 text-xs text-gray-500">
                  Blocks a specific content type for a unit. Students will not be served
                  this content.
                </p>

                <div className="space-y-3">
                  <div>
                    <label className="mb-1 block text-xs font-medium text-gray-600">
                      Unit
                    </label>
                    <select
                      value={blockUnit}
                      onChange={(e) => setBlockUnit(e.target.value)}
                      className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                    >
                      {item?.units.map((u) => (
                        <option key={u.unit_id} value={u.unit_id}>
                          {u.title} ({u.unit_id})
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="mb-1 block text-xs font-medium text-gray-600">
                      Content type
                    </label>
                    <select
                      value={blockType}
                      onChange={(e) => setBlockType(e.target.value)}
                      className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                    >
                      {CONTENT_TYPES.map((t) => (
                        <option key={t} value={t}>
                          {t}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="mb-1 block text-xs font-medium text-gray-600">
                      Reason (optional)
                    </label>
                    <textarea
                      value={reason}
                      onChange={(e) => setReason(e.target.value)}
                      placeholder="Why is this content being blocked?"
                      rows={2}
                      className="w-full resize-none rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                    />
                  </div>
                </div>

                <div className="mt-4 flex gap-3">
                  <button
                    disabled={acting || !blockUnit}
                    onClick={() => {
                      const uid = blockUnit;
                      const ct = blockType;
                      const r = reason || undefined;
                      setModal(null);
                      setReason("");
                      performAction(() => blockVersionContent(version_id, uid, ct, r));
                    }}
                    className="flex-1 rounded-lg bg-gray-700 py-2 text-sm font-medium text-white transition-colors hover:bg-gray-600 disabled:opacity-50"
                  >
                    Confirm block
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
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
