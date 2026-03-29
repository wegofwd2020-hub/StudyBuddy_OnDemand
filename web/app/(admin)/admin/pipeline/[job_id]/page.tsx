"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { getPipelineStatus } from "@/lib/api/curriculum-admin";
import { cn } from "@/lib/utils";
import { ArrowLeft, CheckCircle, XCircle, Loader2 } from "lucide-react";

export default function AdminPipelineJobPage() {
  const { job_id } = useParams<{ job_id: string }>();

  const { data: job, isLoading } = useQuery({
    queryKey: ["admin", "pipeline", job_id],
    queryFn: () => getPipelineStatus(job_id),
    staleTime: 0,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "done" || status === "failed") return false;
      return 5_000;
    },
  });

  const isDone = job?.status === "done";
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

          {/* Progress bar */}
          <div>
            <div className="mb-1.5 flex justify-between text-xs text-gray-500">
              <span>Progress</span>
              <span>{job.progress_pct}%</span>
            </div>
            <div className="h-3 overflow-hidden rounded-full bg-gray-100">
              <div
                className={cn(
                  "h-full rounded-full transition-all duration-500",
                  barColor,
                )}
                style={{ width: `${job.progress_pct}%` }}
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
              <p
                className={cn(
                  "text-2xl font-bold",
                  job.failed > 0 ? "text-red-600" : "text-gray-900",
                )}
              >
                {job.failed}
              </p>
              <p className="mt-0.5 text-xs text-gray-500">Failed</p>
            </div>
          </div>

          {isFailed && job.failed > 0 && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
              {job.failed} unit{job.failed > 1 ? "s" : ""} failed to generate. Check the
              pipeline worker logs for details.
            </div>
          )}
        </div>
      ) : (
        <p className="text-sm text-gray-400">Job not found.</p>
      )}
    </div>
  );
}
