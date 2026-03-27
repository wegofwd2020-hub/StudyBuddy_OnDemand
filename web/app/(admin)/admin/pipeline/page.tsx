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
    <div className="p-8 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Pipeline Jobs</h1>
          <p className="text-sm text-gray-500 mt-0.5">Content generation pipeline status</p>
        </div>
        <Link
          href="/admin/pipeline/trigger"
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg transition-colors"
        >
          <Plus className="h-4 w-4" />
          Trigger job
        </Link>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-14 bg-gray-100 rounded-xl animate-pulse" />
          ))}
        </div>
      ) : data && data.jobs.length > 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Job ID</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Curriculum</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Status</th>
                <th className="text-right px-4 py-3 font-medium text-gray-600">Progress</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Triggered</th>
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
                  <td className="px-4 py-3 text-gray-700 font-mono text-xs">
                    {job.curriculum_id}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={cn(
                        "inline-flex items-center px-2 py-0.5 rounded text-xs font-medium",
                        STATUS_STYLES[job.status] ?? "bg-gray-100 text-gray-600",
                      )}
                    >
                      {job.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <span className="text-gray-700 font-mono text-xs">
                      {job.built}/{job.total}
                      {job.failed > 0 && (
                        <span className="text-red-500 ml-1">({job.failed} failed)</span>
                      )}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-500 text-xs">
                    {new Date(job.triggered_at).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="text-center py-16 text-gray-400">
          <GitBranch className="h-10 w-10 mx-auto mb-3 opacity-40" />
          <p className="text-sm">No pipeline jobs found.</p>
          <Link
            href="/admin/pipeline/trigger"
            className="inline-flex items-center gap-1.5 mt-4 text-sm text-indigo-600 hover:underline"
          >
            <Plus className="h-4 w-4" />
            Trigger your first job
          </Link>
        </div>
      )}

      <button
        onClick={() => refetch()}
        className="mt-4 text-xs text-gray-400 hover:text-gray-600 transition-colors"
      >
        Refresh
      </button>
    </div>
  );
}
