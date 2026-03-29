"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { getPipelineJobs } from "@/lib/api/admin";
import { cn } from "@/lib/utils";
import { GitBranch, Plus } from "lucide-react";

const STATUS_STYLES: Record<string, string> = {
  queued: "bg-gray-100 text-gray-600",
  running: "bg-blue-100 text-blue-700",
  done: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
};

export default function AdminPipelinePage() {
  const { data, isLoading, refetch } = useQuery({
    queryKey: ["admin", "pipeline", "jobs"],
    queryFn: getPipelineJobs,
    staleTime: 15_000,
    refetchInterval: 15_000,
  });

  return (
    <div className="mx-auto max-w-5xl p-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Pipeline Jobs</h1>
          <p className="mt-0.5 text-sm text-gray-500">
            Content generation pipeline status
          </p>
        </div>
        <Link
          href="/admin/pipeline/trigger"
          className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-indigo-500"
        >
          <Plus className="h-4 w-4" />
          Trigger job
        </Link>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-14 animate-pulse rounded-xl bg-gray-100" />
          ))}
        </div>
      ) : data && data.jobs?.length > 0 ? (
        <div className="overflow-hidden rounded-xl border border-gray-200 bg-white">
          <table className="w-full text-sm">
            <thead className="border-b border-gray-200 bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Job ID</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">
                  Curriculum
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Status</th>
                <th className="px-4 py-3 text-right font-medium text-gray-600">
                  Progress
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">
                  Triggered
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {data.jobs.map((job) => (
                <tr key={job.job_id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <Link
                      href={`/admin/pipeline/${job.job_id}`}
                      className="font-mono text-xs text-indigo-600 hover:underline"
                    >
                      {job.job_id.slice(0, 8)}…
                    </Link>
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-gray-700">
                    {job.curriculum_id}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={cn(
                        "inline-flex items-center rounded px-2 py-0.5 text-xs font-medium",
                        STATUS_STYLES[job.status] ?? "bg-gray-100 text-gray-600",
                      )}
                    >
                      {job.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <span className="font-mono text-xs text-gray-700">
                      {job.built}/{job.total}
                      {job.failed > 0 && (
                        <span className="ml-1 text-red-500">({job.failed} failed)</span>
                      )}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-500">
                    {new Date(job.triggered_at).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="py-16 text-center text-gray-400">
          <GitBranch className="mx-auto mb-3 h-10 w-10 opacity-40" />
          <p className="text-sm">No pipeline jobs found.</p>
          <Link
            href="/admin/pipeline/trigger"
            className="mt-4 inline-flex items-center gap-1.5 text-sm text-indigo-600 hover:underline"
          >
            <Plus className="h-4 w-4" />
            Trigger your first job
          </Link>
        </div>
      )}

      <button
        onClick={() => refetch()}
        className="mt-4 text-xs text-gray-400 transition-colors hover:text-gray-600"
      >
        Refresh
      </button>
    </div>
  );
}
