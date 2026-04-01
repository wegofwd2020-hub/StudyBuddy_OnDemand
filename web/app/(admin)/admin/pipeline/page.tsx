"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { getPipelineJobs, AdminPipelineJob } from "@/lib/api/admin";
import { cn } from "@/lib/utils";
import {
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  ChevronDown,
  GitBranch,
  Plus,
  Upload,
  X,
} from "lucide-react";

const STATUS_STYLES: Record<string, string> = {
  queued: "bg-gray-100 text-gray-600",
  running: "bg-blue-100 text-blue-700",
  completed: "bg-green-100 text-green-700",
  done: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
};

const ALL_STATUSES = ["queued", "running", "completed", "done", "failed"];

type SortKey = "triggered_at" | "started_at";
type SortDir = "asc" | "desc";

function duration(start: string | null, end: string | null): string {
  if (!start) return "—";
  const s = new Date(start).getTime();
  const e = end ? new Date(end).getTime() : Date.now();
  const secs = Math.round((e - s) / 1000);
  if (secs < 60) return `${secs}s`;
  const mins = Math.floor(secs / 60);
  const rem = secs % 60;
  return `${mins}m ${rem}s`;
}

function fmtBytes(bytes: number | null): string {
  if (bytes === null || bytes === undefined) return "—";
  if (bytes === 0) return "0 B";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

function SortIcon({
  col,
  sortKey,
  sortDir,
}: {
  col: SortKey;
  sortKey: SortKey;
  sortDir: SortDir;
}) {
  if (sortKey !== col)
    return <ArrowUpDown className="ml-1 inline h-3.5 w-3.5 opacity-40" />;
  return sortDir === "asc" ? (
    <ArrowUp className="ml-1 inline h-3.5 w-3.5 text-indigo-600" />
  ) : (
    <ArrowDown className="ml-1 inline h-3.5 w-3.5 text-indigo-600" />
  );
}

export default function AdminPipelinePage() {
  const { data, isLoading, refetch } = useQuery({
    queryKey: ["admin", "pipeline", "jobs"],
    queryFn: getPipelineJobs,
    staleTime: 10_000,
    refetchInterval: 10_000,
  });

  const [sortKey, setSortKey] = useState<SortKey>("triggered_at");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  // Active filter: only one at a time
  type FilterField = "triggered_by_email" | "status" | null;
  const [filterField, setFilterField] = useState<FilterField>(null);
  const [filterValue, setFilterValue] = useState("");
  const [statusOpen, setStatusOpen] = useState(false);

  function toggleSort(col: SortKey) {
    if (sortKey === col) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(col);
      setSortDir("desc");
    }
  }

  function setFilter(field: FilterField, value = "") {
    setFilterField(field);
    setFilterValue(value);
    setStatusOpen(false);
  }

  function clearFilter() {
    setFilterField(null);
    setFilterValue("");
    setStatusOpen(false);
  }

  const allEmails = useMemo(() => {
    if (!data?.jobs) return [];
    const seen = new Set<string>();
    const result: string[] = [];
    for (const j of data.jobs) {
      const e = j.triggered_by_email ?? "";
      if (e && !seen.has(e)) {
        seen.add(e);
        result.push(e);
      }
    }
    return result.sort();
  }, [data]);

  const processed = useMemo(() => {
    if (!data?.jobs) return [];
    let jobs: AdminPipelineJob[] = [...data.jobs];

    // Filter
    if (filterField === "status" && filterValue) {
      jobs = jobs.filter((j) => j.status === filterValue);
    } else if (filterField === "triggered_by_email" && filterValue) {
      jobs = jobs.filter((j) => (j.triggered_by_email ?? "") === filterValue);
    }

    // Sort
    jobs.sort((a, b) => {
      const av = a[sortKey] ? new Date(a[sortKey]!).getTime() : 0;
      const bv = b[sortKey] ? new Date(b[sortKey]!).getTime() : 0;
      return sortDir === "asc" ? av - bv : bv - av;
    });

    return jobs;
  }, [data, filterField, filterValue, sortKey, sortDir]);

  const activeFilterLabel =
    filterField === "status"
      ? `Status: ${filterValue}`
      : filterField === "triggered_by_email"
        ? `User: ${filterValue}`
        : null;

  return (
    <div className="mx-auto max-w-6xl p-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Pipeline Jobs</h1>
          <p className="mt-0.5 text-sm text-gray-500">
            Content generation history — all admin-triggered builds
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link
            href="/admin/pipeline/upload"
            className="flex items-center gap-2 rounded-lg border border-indigo-300 bg-white px-4 py-2 text-sm font-medium text-indigo-600 transition-colors hover:bg-indigo-50"
          >
            <Upload className="h-4 w-4" />
            Upload Grade JSON
          </Link>
          <Link
            href="/admin/pipeline/trigger"
            className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-indigo-500"
          >
            <Plus className="h-4 w-4" />
            Trigger job
          </Link>
        </div>
      </div>

      {/* Filter bar */}
      {!isLoading && data && data.jobs?.length > 0 && (
        <div className="mb-4 flex flex-wrap items-center gap-2">
          <span className="text-xs font-medium text-gray-500">Filter by:</span>

          {/* Status filter */}
          <div className="relative">
            <button
              onClick={() => {
                setStatusOpen((o) => !o);
                if (filterField !== "status") setFilterField("status");
              }}
              className={cn(
                "flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors",
                filterField === "status" && filterValue
                  ? "border-indigo-400 bg-indigo-50 text-indigo-700"
                  : "border-gray-200 bg-white text-gray-600 hover:border-gray-300",
              )}
            >
              Status
              {filterField === "status" && filterValue ? (
                <span className="ml-1 font-bold">{filterValue}</span>
              ) : null}
              <ChevronDown className="h-3 w-3" />
            </button>
            {statusOpen && (
              <div className="absolute top-full left-0 z-20 mt-1 min-w-[130px] rounded-lg border border-gray-200 bg-white py-1 shadow-lg">
                {ALL_STATUSES.map((s) => (
                  <button
                    key={s}
                    onClick={() => {
                      setFilter("status", s);
                    }}
                    className={cn(
                      "w-full px-3 py-1.5 text-left text-xs hover:bg-gray-50",
                      filterValue === s
                        ? "font-semibold text-indigo-600"
                        : "text-gray-700",
                    )}
                  >
                    {s}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Triggered by filter */}
          {allEmails.length > 0 && (
            <div className="relative">
              <select
                value={filterField === "triggered_by_email" ? filterValue : ""}
                onChange={(e) => {
                  if (e.target.value) setFilter("triggered_by_email", e.target.value);
                  else clearFilter();
                }}
                className={cn(
                  "appearance-none rounded-lg border px-3 py-1.5 pr-7 text-xs font-medium transition-colors",
                  filterField === "triggered_by_email" && filterValue
                    ? "border-indigo-400 bg-indigo-50 text-indigo-700"
                    : "border-gray-200 bg-white text-gray-600 hover:border-gray-300",
                )}
              >
                <option value="">Triggered by</option>
                {allEmails.map((e) => (
                  <option key={e} value={e}>
                    {e}
                  </option>
                ))}
              </select>
              <ChevronDown className="pointer-events-none absolute top-1/2 right-2 h-3 w-3 -translate-y-1/2 text-gray-400" />
            </div>
          )}

          {/* Active filter chip */}
          {activeFilterLabel && (
            <div className="flex items-center gap-1 rounded-full bg-indigo-100 px-2.5 py-1 text-xs font-medium text-indigo-700">
              {activeFilterLabel}
              <button
                onClick={clearFilter}
                className="ml-0.5 rounded-full hover:text-indigo-900"
              >
                <X className="h-3 w-3" />
              </button>
            </div>
          )}

          {activeFilterLabel && (
            <span className="text-xs text-gray-400">
              {processed.length} of {data.jobs.length} jobs
            </span>
          )}
        </div>
      )}

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-14 animate-pulse rounded-xl bg-gray-100" />
          ))}
        </div>
      ) : processed.length > 0 ? (
        <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white">
          <table className="w-full min-w-[1000px] text-sm">
            <thead className="border-b border-gray-200 bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Job</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">
                  Curriculum
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Status</th>
                <th className="px-4 py-3 text-right font-medium text-gray-600">
                  Progress
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">
                  Triggered by
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">
                  <button
                    onClick={() => toggleSort("triggered_at")}
                    className="inline-flex items-center font-medium text-gray-600 hover:text-gray-900"
                  >
                    Uploaded at
                    <SortIcon col="triggered_at" sortKey={sortKey} sortDir={sortDir} />
                  </button>
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">
                  <button
                    onClick={() => toggleSort("started_at")}
                    className="inline-flex items-center font-medium text-gray-600 hover:text-gray-900"
                  >
                    Started at
                    <SortIcon col="started_at" sortKey={sortKey} sortDir={sortDir} />
                  </button>
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">
                  Duration
                </th>
                <th className="px-4 py-3 text-right font-medium text-gray-600">
                  Payload
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {processed.map((job) => (
                <tr key={job.job_id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <Link
                      href={`/admin/pipeline/${job.job_id}`}
                      className="font-mono text-xs text-indigo-600 hover:underline"
                    >
                      {job.job_id.slice(0, 8)}…
                    </Link>
                    <p className="mt-0.5 font-mono text-xs text-gray-400">
                      {job.langs}
                      {job.force ? " · force" : ""}
                    </p>
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
                    {job.error && (
                      <p
                        className="mt-0.5 max-w-[180px] truncate text-xs text-red-500"
                        title={job.error}
                      >
                        {job.error}
                      </p>
                    )}
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
                    {job.triggered_by_email ?? "—"}
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-500">
                    {job.triggered_at ? new Date(job.triggered_at).toLocaleString() : "—"}
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-500">
                    {job.started_at ? new Date(job.started_at).toLocaleString() : "—"}
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-500">
                    {duration(job.started_at, job.completed_at)}
                  </td>
                  <td className="px-4 py-3 text-right font-mono text-xs text-gray-500">
                    {fmtBytes(job.payload_bytes)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : data && data.jobs?.length > 0 ? (
        <div className="py-10 text-center text-gray-400">
          <p className="text-sm">No jobs match the current filter.</p>
          <button
            onClick={clearFilter}
            className="mt-2 text-xs text-indigo-600 hover:underline"
          >
            Clear filter
          </button>
        </div>
      ) : (
        <div className="py-16 text-center text-gray-400">
          <GitBranch className="mx-auto mb-3 h-10 w-10 opacity-40" />
          <p className="text-sm">No pipeline jobs yet.</p>
          <Link
            href="/admin/pipeline/upload"
            className="mt-4 inline-flex items-center gap-1.5 text-sm text-indigo-600 hover:underline"
          >
            <Upload className="h-4 w-4" />
            Upload a grade JSON to get started
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
