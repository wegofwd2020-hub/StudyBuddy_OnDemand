"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { getAdminPipelineJobStatus } from "@/lib/api/admin";

function fmtBytes(bytes: number | null | undefined): string {
  if (bytes === null || bytes === undefined) return "—";
  if (bytes === 0) return "0 B";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}
import { cn } from "@/lib/utils";
import { ArrowLeft, CheckCircle, XCircle, Loader2 } from "lucide-react";

export default function AdminPipelineJobPage() {
  const { job_id } = useParams<{ job_id: string }>();

  const { data: job, isLoading } = useQuery({
    queryKey: ["admin", "pipeline", job_id],
    queryFn: () => getAdminPipelineJobStatus(job_id),
    staleTime: 0,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "done" || status === "completed" || status === "failed") return false;
      return 5_000;
    },
  });

  const isDone = job?.status === "done" || job?.status === "completed";
  const isFailed = job?.status === "failed";

  const barColor =
    isFailed && (job?.failed ?? 0) > 0
      ? "bg-red-500"
      : isDone
        ? "bg-green-500"
        : "bg-indigo-500";

  return (
    <div className="mx-auto max-w-2xl p-8">
      <Link
        href="/admin/pipeline"
        className="mb-6 inline-flex items-center gap-1.5 text-sm text-gray-500 transition-colors hover:text-gray-900"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to pipeline
      </Link>

      <h1 className="mb-1 text-2xl font-bold text-gray-900">Pipeline Job</h1>
      <p className="mb-8 font-mono text-xs text-gray-400">{job_id}</p>

      {isLoading ? (
        <div className="h-40 animate-pulse rounded-xl bg-gray-100" />
      ) : job ? (
        <div className="space-y-6 rounded-xl border border-gray-200 bg-white p-6">
          {/* Status */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {isDone ? (
                <CheckCircle className="h-5 w-5 text-green-500" />
              ) : isFailed ? (
                <XCircle className="h-5 w-5 text-red-500" />
              ) : (
                <Loader2 className="h-5 w-5 animate-spin text-indigo-500" />
              )}
              <span className="font-semibold text-gray-900 capitalize">{job.status}</span>
            </div>
            <span className="font-mono text-xs text-gray-400">{job.curriculum_id}</span>
          </div>

          {/* Timestamps */}
          <div className="grid grid-cols-2 gap-3 text-xs text-gray-500">
            <div>
              <p className="font-medium text-gray-600">Triggered</p>
              <p>{job.triggered_at ? new Date(job.triggered_at).toLocaleString() : "—"}</p>
            </div>
            <div>
              <p className="font-medium text-gray-600">Started</p>
              <p>{job.started_at ? new Date(job.started_at).toLocaleString() : "—"}</p>
            </div>
            <div>
              <p className="font-medium text-gray-600">Completed</p>
              <p>{job.completed_at ? new Date(job.completed_at).toLocaleString() : "—"}</p>
            </div>
            <div>
              <p className="font-medium text-gray-600">Languages</p>
              <p className="font-mono">{job.langs ?? "—"}</p>
            </div>
            <div>
              <p className="font-medium text-gray-600">Payload size</p>
              <p className="font-mono">{fmtBytes(job.payload_bytes)}</p>
            </div>
            <div>
              <p className="font-medium text-gray-600">Duration</p>
              <p className="font-mono">
                {job.started_at && job.completed_at
                  ? (() => {
                      const s = new Date(job.started_at).getTime();
                      const e = new Date(job.completed_at).getTime();
                      const secs = Math.round((e - s) / 1000);
                      return secs < 60 ? `${secs}s` : `${Math.floor(secs / 60)}m ${secs % 60}s`;
                    })()
                  : "—"}
              </p>
            </div>
          </div>

          {/* Progress bar */}
          <div>
            <div className="mb-1.5 flex justify-between text-xs text-gray-500">
              <span>Progress</span>
              <span>{job.progress_pct ?? 0}%</span>
            </div>
            <div className="h-3 overflow-hidden rounded-full bg-gray-100">
              <div
                className={cn("h-full rounded-full transition-all duration-500", barColor)}
                style={{ width: `${job.progress_pct ?? 0}%` }}
              />
            </div>
          </div>

          {/* Counts */}
          <div className="grid grid-cols-3 gap-4 text-center">
            <div className="rounded-lg bg-gray-50 p-3">
              <p className="text-2xl font-bold text-gray-900">{job.built}</p>
              <p className="mt-0.5 text-xs text-gray-500">Built</p>
            </div>
            <div className="rounded-lg bg-gray-50 p-3">
              <p className="text-2xl font-bold text-gray-900">{job.total}</p>
              <p className="mt-0.5 text-xs text-gray-500">Total</p>
            </div>
            <div className="rounded-lg bg-gray-50 p-3">
              <p className={cn("text-2xl font-bold", (job.failed ?? 0) > 0 ? "text-red-600" : "text-gray-900")}>
                {job.failed ?? 0}
              </p>
              <p className="mt-0.5 text-xs text-gray-500">Failed</p>
            </div>
          </div>

          {job.error && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
              <p className="font-medium">Error</p>
              <p className="mt-1">{job.error}</p>
            </div>
          )}

          {isDone && (
            <div className="rounded-lg border border-green-200 bg-green-50 p-4 text-sm text-green-700">
              Build complete. Content is now available in the{" "}
              <a href="/admin/content-review" className="font-medium underline">
                Content Review queue
              </a>{" "}
              as <strong>pending</strong>.
            </div>
          )}
        </div>
      ) : (
        <p className="text-sm text-gray-400">Job not found.</p>
      )}
    </div>
  );
}
