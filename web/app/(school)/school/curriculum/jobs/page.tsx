"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTeacher } from "@/lib/hooks/useTeacher";
import { listSchoolPipelineJobs, type PipelineJob } from "@/lib/api/school-admin";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { LinkButton } from "@/components/ui/link-button";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

// ── Status badge ──────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    queued: "bg-gray-100 text-gray-600",
    running: "bg-blue-100 text-blue-700",
    done: "bg-green-100 text-green-700",
    failed: "bg-red-100 text-red-700",
  };
  const label: Record<string, string> = {
    queued: "Queued",
    running: "Running",
    done: "Done",
    failed: "Failed",
  };
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium",
        styles[status] ?? "bg-gray-100 text-gray-600",
      )}
    >
      {status === "running" && <Loader2 className="h-3 w-3 animate-spin" />}
      {label[status] ?? status}
    </span>
  );
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtDate(iso: string | null) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function fmtBytes(n: number | null) {
  if (n == null) return "—";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

// ── Page ──────────────────────────────────────────────────────────────────────

const PAGE_SIZE = 20;

export default function JobsListPage() {
  const teacher = useTeacher();
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<string>("");

  const schoolId = teacher?.school_id ?? "";

  const { data, isLoading } = useQuery({
    queryKey: ["school-pipeline-jobs", schoolId, page, statusFilter],
    queryFn: () =>
      listSchoolPipelineJobs(schoolId, {
        page,
        page_size: PAGE_SIZE,
        status: statusFilter || undefined,
      }),
    enabled: !!schoolId,
    // Poll while any job is running
    refetchInterval: (query) => {
      const jobs: PipelineJob[] = query.state.data?.jobs ?? [];
      return jobs.some((j) => j.status === "running" || j.status === "queued")
        ? 5_000
        : false;
    },
    staleTime: 0,
  });

  const jobs = data?.jobs ?? [];
  const total = data?.total ?? 0;
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="max-w-5xl space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <LinkButton href="/school/curriculum" variant="outline" size="sm">
            ← Curriculum
          </LinkButton>
          <h1 className="text-2xl font-bold text-gray-900">Pipeline Jobs</h1>
        </div>

        {/* Status filter */}
        <select
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value);
            setPage(1);
          }}
          className="h-8 rounded-md border border-gray-200 bg-white px-3 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
        >
          <option value="">All statuses</option>
          <option value="queued">Queued</option>
          <option value="running">Running</option>
          <option value="done">Done</option>
          <option value="failed">Failed</option>
        </select>
      </div>

      <Card className="border shadow-sm">
        <CardHeader className="pb-2">
          <CardTitle className="text-base">
            {total} job{total !== 1 ? "s" : ""}
            {statusFilter ? ` — ${statusFilter}` : ""}
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
            </div>
          ) : jobs.length === 0 ? (
            <p className="py-10 text-center text-sm text-gray-400">No jobs found.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-gray-50">
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">
                      Status
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">
                      Grade / Langs
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">
                      Progress
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">
                      Size
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">
                      Triggered
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">
                      Completed
                    </th>
                    <th className="w-16 px-4 py-3" />
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {jobs.map((job) => {
                    const pct =
                      job.total && job.total > 0
                        ? Math.min(
                            ((job.built ?? 0) / job.total) * 100,
                            100,
                          )
                        : 0;
                    return (
                      <tr key={job.job_id} className="hover:bg-gray-50">
                        <td className="px-4 py-3">
                          <StatusBadge status={job.status} />
                        </td>
                        <td className="px-4 py-3 text-gray-700">
                          {job.grade ? `Grade ${job.grade}` : "—"}
                          <span className="ml-1.5 font-mono text-xs text-gray-400 uppercase">
                            {job.langs}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          {job.total ? (
                            <div className="flex items-center gap-2">
                              <div className="h-1.5 w-20 overflow-hidden rounded-full bg-gray-100">
                                <div
                                  className={cn(
                                    "h-full rounded-full",
                                    job.status === "failed" && (job.failed ?? 0) > 0
                                      ? "bg-red-400"
                                      : job.status === "done"
                                        ? "bg-green-500"
                                        : "bg-blue-500",
                                  )}
                                  style={{ width: `${pct}%` }}
                                />
                              </div>
                              <span className="text-xs text-gray-500">
                                {job.built ?? 0}/{job.total}
                              </span>
                            </div>
                          ) : (
                            <span className="text-xs text-gray-400">—</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-xs text-gray-500">
                          {fmtBytes(job.payload_bytes)}
                        </td>
                        <td className="px-4 py-3 text-xs text-gray-500">
                          {fmtDate(job.triggered_at)}
                        </td>
                        <td className="px-4 py-3 text-xs text-gray-500">
                          {fmtDate(job.completed_at)}
                        </td>
                        <td className="px-4 py-3">
                          <LinkButton
                            href={`/school/curriculum/jobs/${job.job_id}`}
                            variant="outline"
                            size="sm"
                            className="h-6 px-2 text-xs"
                          >
                            View
                          </LinkButton>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Pagination */}
      {pageCount > 1 && (
        <div className="flex items-center justify-center gap-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="rounded-md border border-gray-200 px-3 py-1.5 text-xs disabled:opacity-40 hover:bg-gray-50"
          >
            ← Prev
          </button>
          <span className="text-xs text-gray-500">
            Page {page} of {pageCount}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(pageCount, p + 1))}
            disabled={page === pageCount}
            className="rounded-md border border-gray-200 px-3 py-1.5 text-xs disabled:opacity-40 hover:bg-gray-50"
          >
            Next →
          </button>
        </div>
      )}
    </div>
  );
}
