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

  const barColor = isFailed && (job?.failed ?? 0) > 0
    ? "bg-red-500"
    : isDone
    ? "bg-green-500"
    : "bg-indigo-500";

  return (
    <div className="p-8 max-w-2xl mx-auto">
      <Link
        href="/admin/pipeline"
        className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-900 mb-6 transition-colors"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to pipeline
      </Link>

      <h1 className="text-2xl font-bold text-gray-900 mb-1">Pipeline Job</h1>
      <p className="text-xs text-gray-400 font-mono mb-8">{job_id}</p>

      {isLoading ? (
        <div className="h-40 bg-gray-100 rounded-xl animate-pulse" />
      ) : job ? (
        <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-6">
          {/* Status */}
          <div className="flex items-center gap-3">
            {isDone ? (
              <CheckCircle className="h-5 w-5 text-green-500" />
            ) : isFailed ? (
              <XCircle className="h-5 w-5 text-red-500" />
            ) : (
              <Loader2 className="h-5 w-5 text-indigo-500 animate-spin" />
            )}
            <span className="font-semibold text-gray-900 capitalize">{job.status}</span>
          </div>

          {/* Progress bar */}
          <div>
            <div className="flex justify-between text-xs text-gray-500 mb-1.5">
              <span>Progress</span>
              <span>{job.progress_pct}%</span>
            </div>
            <div className="h-3 bg-gray-100 rounded-full overflow-hidden">
              <div
                className={cn("h-full rounded-full transition-all duration-500", barColor)}
                style={{ width: `${job.progress_pct}%` }}
              />
            </div>
          </div>

          {/* Counts */}
          <div className="grid grid-cols-3 gap-4 text-center">
            <div className="bg-gray-50 rounded-lg p-3">
              <p className="text-2xl font-bold text-gray-900">{job.built}</p>
              <p className="text-xs text-gray-500 mt-0.5">Built</p>
            </div>
            <div className="bg-gray-50 rounded-lg p-3">
              <p className="text-2xl font-bold text-gray-900">{job.total}</p>
              <p className="text-xs text-gray-500 mt-0.5">Total</p>
            </div>
            <div className="bg-gray-50 rounded-lg p-3">
              <p
                className={cn(
                  "text-2xl font-bold",
                  job.failed > 0 ? "text-red-600" : "text-gray-900",
                )}
              >
                {job.failed}
              </p>
              <p className="text-xs text-gray-500 mt-0.5">Failed</p>
            </div>
          </div>

          {isFailed && job.failed > 0 && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
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
