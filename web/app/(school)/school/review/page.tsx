"use client";

import { Fragment, useState } from "react";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTeacher } from "@/lib/hooks/useTeacher";
import {
  listReviewQueue,
  approveUnitContent,
  rejectUnitContent,
  type ReviewQueueItem,
} from "@/lib/api/school-admin";
import {
  ClipboardCheck,
  ThumbsUp,
  ThumbsDown,
  ExternalLink,
  CheckCircle2,
  AlertCircle,
  Inbox,
} from "lucide-react";

// ── Content type labels ────────────────────────────────────────────────────────

const CONTENT_TYPE_LABELS: Record<string, string> = {
  lesson: "Lesson",
  tutorial: "Tutorial",
  quiz_set_1: "Quiz 1",
  quiz_set_2: "Quiz 2",
  quiz_set_3: "Quiz 3",
  experiment: "Experiment",
};

// ── Row ────────────────────────────────────────────────────────────────────────

function QueueRow({
  item,
  schoolId,
  onDone,
}: {
  item: ReviewQueueItem;
  schoolId: string;
  onDone: (overrideId: string) => void;
}) {
  const [showReject, setShowReject] = useState(false);
  const [reason, setReason] = useState("");
  const [rowError, setRowError] = useState<string | null>(null);

  const editHref = `/school/content/${item.forked_curriculum_id}/units/${item.unit_id}/edit${item.adoption_id ? `?aid=${item.adoption_id}` : ""}`;

  const approveMutation = useMutation({
    mutationFn: () => {
      const ok = window.confirm(
        `Approve and publish "${item.unit_title ?? item.unit_id}" (${CONTENT_TYPE_LABELS[item.content_type] ?? item.content_type})? It will be immediately visible to students.`,
      );
      if (!ok) return Promise.reject(new Error("cancelled"));
      return approveUnitContent(
        schoolId,
        item.forked_curriculum_id,
        item.unit_id,
        true,
        item.content_type,
      );
    },
    onSuccess: () => onDone(item.override_id),
    onError: (err: Error) => {
      if (err.message !== "cancelled") setRowError(err.message);
    },
  });

  const rejectMutation = useMutation({
    mutationFn: () =>
      rejectUnitContent(
        schoolId,
        item.forked_curriculum_id,
        item.unit_id,
        reason,
        item.content_type,
      ),
    onSuccess: () => onDone(item.override_id),
    onError: (err: Error) => setRowError(err.message),
  });

  return (
    <>
      <tr className="border-b border-gray-100 hover:bg-gray-50">
        {/* Unit */}
        <td className="py-3 pr-3 pl-4 text-sm font-medium text-gray-900">
          {item.unit_title ?? item.unit_id}
        </td>
        {/* Subject */}
        <td className="px-3 py-3 text-sm text-gray-500">{item.subject_name ?? "—"}</td>
        {/* Content type */}
        <td className="px-3 py-3">
          <span className="inline-flex items-center rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-700">
            {CONTENT_TYPE_LABELS[item.content_type] ?? item.content_type}
          </span>
        </td>
        {/* Submitted by */}
        <td className="px-3 py-3 text-sm text-gray-500">
          {item.submitted_by_name ?? "—"}
        </td>
        {/* Submitted at */}
        <td className="px-3 py-3 text-xs text-gray-400 tabular-nums">
          {new Date(item.submitted_at).toLocaleDateString(undefined, {
            month: "short",
            day: "numeric",
            year: "numeric",
          })}
        </td>
        {/* Actions */}
        <td className="py-3 pr-4 pl-3">
          <div className="flex items-center justify-end gap-2">
            <Link
              href={editHref}
              className="inline-flex items-center gap-1 rounded-md border border-gray-200 bg-white px-2.5 py-1 text-xs font-medium text-gray-600 shadow-sm hover:bg-gray-50"
              title="Open full editor"
            >
              <ExternalLink className="h-3 w-3" />
              View
            </Link>
            <button
              type="button"
              onClick={() => {
                setShowReject((v) => !v);
                setRowError(null);
              }}
              disabled={rejectMutation.isPending || approveMutation.isPending}
              className="inline-flex items-center gap-1 rounded-md border border-red-200 bg-white px-2.5 py-1 text-xs font-medium text-red-600 shadow-sm hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <ThumbsDown className="h-3 w-3" />
              Reject
            </button>
            <button
              type="button"
              onClick={() => {
                setRowError(null);
                approveMutation.mutate();
              }}
              disabled={approveMutation.isPending || rejectMutation.isPending}
              className="inline-flex items-center gap-1 rounded-md bg-green-600 px-2.5 py-1 text-xs font-medium text-white shadow-sm hover:bg-green-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <ThumbsUp className="h-3 w-3" />
              {approveMutation.isPending ? "…" : "Approve"}
            </button>
          </div>
        </td>
      </tr>

      {/* Reject reason row */}
      {showReject && (
        <tr className="border-b border-red-100 bg-red-50">
          <td colSpan={6} className="px-4 py-3">
            <div className="flex items-start gap-3">
              <textarea
                rows={2}
                className="flex-1 rounded-md border border-red-200 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-red-400 focus:ring-1 focus:ring-red-400 focus:outline-none"
                placeholder="Reason for rejection — the teacher will see this…"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
              />
              <div className="flex flex-col gap-1.5">
                <button
                  type="button"
                  onClick={() => rejectMutation.mutate()}
                  disabled={rejectMutation.isPending || !reason.trim()}
                  className="rounded-md bg-red-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {rejectMutation.isPending ? "…" : "Confirm"}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowReject(false);
                    setReason("");
                  }}
                  className="text-xs text-gray-400 hover:text-gray-600"
                >
                  Cancel
                </button>
              </div>
            </div>
            {rowError && <p className="mt-1.5 text-xs text-red-600">{rowError}</p>}
          </td>
        </tr>
      )}
    </>
  );
}

// ── Page ───────────────────────────────────────────────────────────────────────

export default function ReviewQueuePage() {
  const teacher = useTeacher();
  const schoolId = teacher?.school_id ?? "";
  const queryClient = useQueryClient();

  const [dismissed, setDismissed] = useState<Set<string>>(new Set());
  const [notice, setNotice] = useState<string | null>(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ["review-queue", schoolId],
    queryFn: () => listReviewQueue(schoolId),
    enabled: !!schoolId,
    staleTime: 30_000,
    refetchInterval: 60_000,
  });

  function handleDone(overrideId: string) {
    setDismissed((prev) => new Set(prev).add(overrideId));
    setNotice("Done — item removed from queue.");
    queryClient.invalidateQueries({ queryKey: ["review-queue", schoolId] });
    setTimeout(() => setNotice(null), 3000);
  }

  const items = (data?.items ?? []).filter((i) => !dismissed.has(i.override_id));

  // Group by curriculum
  const curricula = Array.from(
    new Map(items.map((i) => [i.forked_curriculum_id, i])).values(),
  ).map((i) => ({
    id: i.forked_curriculum_id,
    name: i.curriculum_name,
    grade: i.grade,
  }));

  return (
    <div className="max-w-5xl space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <ClipboardCheck className="h-6 w-6 text-indigo-600" />
        <div>
          <h1 className="text-xl font-bold text-gray-900">Review Queue</h1>
          <p className="text-sm text-gray-500">
            All pending content submissions across your curricula
          </p>
        </div>
        {!isLoading && data && (
          <span className="ml-auto inline-flex items-center rounded-full bg-indigo-100 px-2.5 py-0.5 text-sm font-semibold text-indigo-700">
            {items.length} pending
          </span>
        )}
      </div>

      {/* Notice */}
      {notice && (
        <div className="flex items-center gap-2 rounded-md border border-green-200 bg-green-50 px-4 py-2.5 text-sm text-green-800">
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          {notice}
        </div>
      )}

      {isLoading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-12 animate-pulse rounded-lg bg-gray-100" />
          ))}
        </div>
      ) : error ? (
        <div className="flex items-center gap-2 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          <AlertCircle className="h-4 w-4 shrink-0" />
          Failed to load the review queue. Please refresh.
        </div>
      ) : items.length === 0 ? (
        <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed border-gray-200 py-16 text-center">
          <Inbox className="h-10 w-10 text-gray-300" />
          <p className="text-sm font-medium text-gray-500">Queue is empty</p>
          <p className="max-w-xs text-xs text-gray-400">
            No content submissions are waiting for review. Items appear here when a
            teacher submits a draft.
          </p>
        </div>
      ) : (
        <div className="space-y-6">
          {curricula.map((cur) => {
            const curItems = items.filter((i) => i.forked_curriculum_id === cur.id);
            return (
              <div
                key={cur.id}
                className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm"
              >
                {/* Curriculum header */}
                <div className="flex items-center gap-2 border-b border-gray-100 bg-gray-50 px-4 py-2.5">
                  <span className="text-sm font-semibold text-gray-700">
                    {cur.name ?? "Unknown curriculum"}
                  </span>
                  {cur.grade !== null && cur.grade !== undefined && (
                    <span className="rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-600">
                      Grade {cur.grade}
                    </span>
                  )}
                  <span className="ml-auto text-xs text-gray-400">
                    {curItems.length} {curItems.length === 1 ? "item" : "items"}
                  </span>
                </div>

                {/* Table */}
                <table className="min-w-full">
                  <thead>
                    <tr className="border-b border-gray-100 bg-white">
                      <th className="py-2.5 pr-3 pl-4 text-left text-xs font-semibold tracking-wide text-gray-400 uppercase">
                        Unit
                      </th>
                      <th className="px-3 py-2.5 text-left text-xs font-semibold tracking-wide text-gray-400 uppercase">
                        Subject
                      </th>
                      <th className="px-3 py-2.5 text-left text-xs font-semibold tracking-wide text-gray-400 uppercase">
                        Type
                      </th>
                      <th className="px-3 py-2.5 text-left text-xs font-semibold tracking-wide text-gray-400 uppercase">
                        Submitted by
                      </th>
                      <th className="px-3 py-2.5 text-left text-xs font-semibold tracking-wide text-gray-400 uppercase">
                        Date
                      </th>
                      <th className="relative py-2.5 pr-4 pl-3">
                        <span className="sr-only">Actions</span>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {curItems.map((item) => (
                      <QueueRow
                        key={item.override_id}
                        item={item}
                        schoolId={schoolId}
                        onDone={handleDone}
                      />
                    ))}
                  </tbody>
                </table>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
