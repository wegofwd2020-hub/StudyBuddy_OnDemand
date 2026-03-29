"use client";

import { useQuery } from "@tanstack/react-query";
import { getCiReports, type CiJob, type CiRun } from "@/lib/api/admin";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  CheckCircle2,
  XCircle,
  Clock,
  GitBranch,
  GitCommit,
  ExternalLink,
  RefreshCw,
  AlertCircle,
  Loader2,
  Settings2,
} from "lucide-react";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function fmtDuration(seconds: number | null): string {
  if (seconds === null) return "—";
  if (seconds < 60) return `${seconds}s`;
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return s > 0 ? `${m}m ${s}s` : `${m}m`;
}

function fmtDate(iso: string): string {
  try {
    return new Intl.DateTimeFormat(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

function timeAgo(iso: string): string {
  try {
    const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
    if (diff < 60) return "just now";
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return `${Math.floor(diff / 86400)}d ago`;
  } catch {
    return "";
  }
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function ConclusionBadge({ conclusion }: { conclusion: string | null }) {
  if (!conclusion) {
    return (
      <Badge className="border-yellow-200 bg-yellow-50 text-yellow-700">
        <Loader2 className="mr-1 h-3 w-3 animate-spin" />
        Running
      </Badge>
    );
  }
  if (conclusion === "success") {
    return (
      <Badge className="border-green-200 bg-green-50 text-green-700">
        <CheckCircle2 className="mr-1 h-3 w-3" />
        Passed
      </Badge>
    );
  }
  if (conclusion === "cancelled" || conclusion === "skipped") {
    return (
      <Badge className="border-gray-200 bg-gray-100 text-gray-500">
        <Clock className="mr-1 h-3 w-3" />
        {conclusion.charAt(0).toUpperCase() + conclusion.slice(1)}
      </Badge>
    );
  }
  return (
    <Badge className="border-red-200 bg-red-50 text-red-700">
      <XCircle className="mr-1 h-3 w-3" />
      Failed
    </Badge>
  );
}

function LatestRunBanner({ run }: { run: CiRun }) {
  const passed = run.conclusion === "success";
  const running = !run.conclusion;

  return (
    <div
      className={`rounded-lg border p-5 ${
        running
          ? "border-yellow-200 bg-yellow-50"
          : passed
            ? "border-green-200 bg-green-50"
            : "border-red-200 bg-red-50"
      }`}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          {running ? (
            <Loader2 className="h-7 w-7 animate-spin text-yellow-500" />
          ) : passed ? (
            <CheckCircle2 className="h-7 w-7 text-green-600" />
          ) : (
            <XCircle className="h-7 w-7 text-red-600" />
          )}
          <div>
            <p
              className={`text-lg font-bold ${
                running ? "text-yellow-800" : passed ? "text-green-800" : "text-red-800"
              }`}
            >
              {running
                ? "Build in progress"
                : passed
                  ? "All checks passed"
                  : "Build failed"}
            </p>
            <p className="mt-0.5 text-sm text-gray-600">{timeAgo(run.created_at)}</p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-4 text-sm text-gray-600">
          <span className="flex items-center gap-1.5">
            <GitBranch className="h-3.5 w-3.5" />
            {run.head_branch}
          </span>
          <span className="flex items-center gap-1.5 font-mono">
            <GitCommit className="h-3.5 w-3.5" />
            {run.head_sha}
          </span>
          {run.duration_s !== null && (
            <span className="flex items-center gap-1.5">
              <Clock className="h-3.5 w-3.5" />
              {fmtDuration(run.duration_s)}
            </span>
          )}
          <a
            href={run.html_url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-indigo-600 hover:underline"
          >
            View on GitHub
            <ExternalLink className="h-3.5 w-3.5" />
          </a>
        </div>
      </div>
    </div>
  );
}

function JobsTable({ jobs }: { jobs: CiJob[] }) {
  return (
    <Card className="border shadow-sm">
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Job Breakdown — Latest Run</CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-left text-xs font-medium tracking-wide text-gray-500 uppercase">
                <th className="px-4 py-2.5">Job</th>
                <th className="px-4 py-2.5">Result</th>
                <th className="px-4 py-2.5">Duration</th>
                <th className="px-4 py-2.5">Details</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((job, i) => (
                <tr key={i} className="border-b last:border-0 hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900">{job.name}</td>
                  <td className="px-4 py-3">
                    <ConclusionBadge conclusion={job.conclusion} />
                  </td>
                  <td className="px-4 py-3 text-gray-500">
                    {fmtDuration(job.duration_s)}
                  </td>
                  <td className="px-4 py-3">
                    <a
                      href={job.html_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-1 text-indigo-600 hover:underline"
                    >
                      Logs
                      <ExternalLink className="h-3 w-3" />
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}

function RunHistoryTable({ runs }: { runs: CiRun[] }) {
  return (
    <Card className="border shadow-sm">
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Run History</CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-left text-xs font-medium tracking-wide text-gray-500 uppercase">
                <th className="px-4 py-2.5">Run</th>
                <th className="px-4 py-2.5">Branch</th>
                <th className="px-4 py-2.5">Commit</th>
                <th className="px-4 py-2.5">Result</th>
                <th className="px-4 py-2.5">Duration</th>
                <th className="px-4 py-2.5">Triggered</th>
                <th className="px-4 py-2.5"></th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => (
                <tr key={run.run_id} className="border-b last:border-0 hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono text-xs text-gray-500">
                    #{run.run_id}
                  </td>
                  <td className="px-4 py-3">
                    <span className="flex items-center gap-1 text-gray-700">
                      <GitBranch className="h-3 w-3 text-gray-400" />
                      {run.head_branch}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-gray-500">
                    {run.head_sha}
                  </td>
                  <td className="px-4 py-3">
                    <ConclusionBadge conclusion={run.conclusion} />
                  </td>
                  <td className="px-4 py-3 text-gray-500">
                    {fmtDuration(run.duration_s)}
                  </td>
                  <td className="px-4 py-3 text-gray-500">{fmtDate(run.created_at)}</td>
                  <td className="px-4 py-3">
                    <a
                      href={run.html_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-1 text-indigo-600 hover:underline"
                    >
                      <ExternalLink className="h-3.5 w-3.5" />
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}

function NotConfiguredCard() {
  return (
    <Card className="border border-dashed shadow-none">
      <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
        <Settings2 className="h-10 w-10 text-gray-300" />
        <p className="text-base font-medium text-gray-600">
          GitHub integration not configured
        </p>
        <p className="max-w-sm text-sm text-gray-400">
          Set <code className="rounded bg-gray-100 px-1 py-0.5 text-xs">GITHUB_REPO</code>{" "}
          (e.g.{" "}
          <code className="rounded bg-gray-100 px-1 py-0.5 text-xs">owner/repo</code>) in
          your backend environment variables. Optionally set{" "}
          <code className="rounded bg-gray-100 px-1 py-0.5 text-xs">GITHUB_TOKEN</code> to
          raise the API rate limit.
        </p>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function BuildReportsPage() {
  const { data, isLoading, isError, refetch, isFetching, dataUpdatedAt } = useQuery({
    queryKey: ["ci-reports"],
    queryFn: getCiReports,
    staleTime: 5 * 60 * 1000, // 5 min — matches backend Redis cache
    refetchOnWindowFocus: false,
  });

  const latest = data?.runs[0] ?? null;

  return (
    <div className="max-w-5xl space-y-6 p-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Build &amp; Test Reports</h1>
          {dataUpdatedAt > 0 && (
            <p className="mt-0.5 text-xs text-gray-400">
              Data cached · last fetched {timeAgo(new Date(dataUpdatedAt).toISOString())}
            </p>
          )}
        </div>
        <button
          onClick={() => refetch()}
          disabled={isFetching}
          className="flex items-center gap-1.5 rounded-md border border-gray-300 px-3 py-1.5 text-sm text-gray-600 transition hover:bg-gray-50 disabled:opacity-50"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${isFetching ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      {/* Error */}
      {isError && (
        <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          <AlertCircle className="h-4 w-4 shrink-0" />
          Could not load CI reports. Check that GitHub credentials are valid.
        </div>
      )}

      {/* Loading */}
      {isLoading && (
        <div className="space-y-4">
          <Skeleton className="h-24 rounded-lg" />
          <Skeleton className="h-48 rounded-lg" />
          <Skeleton className="h-64 rounded-lg" />
        </div>
      )}

      {/* Not configured */}
      {data && !data.github_configured && <NotConfiguredCard />}

      {/* Configured & has data */}
      {data?.github_configured && (
        <>
          {/* Repo label */}
          <p className="text-xs text-gray-400">
            Repository:{" "}
            <a
              href={`https://github.com/${data.repo}`}
              target="_blank"
              rel="noopener noreferrer"
              className="font-medium text-indigo-600 hover:underline"
            >
              {data.repo}
            </a>
          </p>

          {/* Latest run banner */}
          {latest && <LatestRunBanner run={latest} />}

          {/* Jobs breakdown */}
          {latest && latest.jobs.length > 0 && <JobsTable jobs={latest.jobs} />}

          {/* History */}
          {data.runs.length > 0 && <RunHistoryTable runs={data.runs} />}

          {data.runs.length === 0 && (
            <p className="text-sm text-gray-400">
              No CI runs found on the main branch yet.
            </p>
          )}
        </>
      )}
    </div>
  );
}
