"use client";

import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { useTeacher } from "@/lib/hooks/useTeacher";
import { getSchoolPipelineJob, triggerSchoolPipeline } from "@/lib/api/school-admin";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { LinkButton } from "@/components/ui/link-button";
import { CheckCircle, XCircle, Loader2, Clock, RotateCcw } from "lucide-react";
import { cn } from "@/lib/utils";
import { useState } from "react";
import { useRouter } from "next/navigation";

// ── Status icon ───────────────────────────────────────────────────────────────

function StatusIcon({ status }: { status: string }) {
  if (status === "done") return <CheckCircle className="h-5 w-5 text-green-500" />;
  if (status === "failed") return <XCircle className="h-5 w-5 text-red-500" />;
  if (status === "running") return <Loader2 className="h-5 w-5 animate-spin text-blue-500" />;
  return <Clock className="h-5 w-5 text-gray-400" />;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtDate(iso: string | null) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function fmtBytes(n: number | null) {
  if (n == null) return "—";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

function duration(start: string | null, end: string | null): string {
  if (!start || !end) return "—";
  const ms = new Date(end).getTime() - new Date(start).getTime();
  if (ms < 60_000) return `${Math.round(ms / 1000)}s`;
  return `${Math.floor(ms / 60_000)}m ${Math.round((ms % 60_000) / 1000)}s`;
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function JobDetailPage() {
  const { job_id } = useParams<{ job_id: string }>();
  const teacher = useTeacher();
  const router = useRouter();
  const [retrying, setRetrying] = useState(false);

  const schoolId = teacher?.school_id ?? "";

  const { data, isLoading } = useQuery({
    queryKey: ["school-pipeline-job", schoolId, job_id],
    queryFn: () => getSchoolPipelineJob(schoolId, job_id),
    enabled: !!schoolId && !!job_id,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "done" || status === "failed") return false;
      return 5_000;
    },
    staleTime: 0,
  });

  const isDone = data?.status === "done";
  const isFailed = data?.status === "failed";
  const isRunning = data?.status === "running";
  const isFinished = isDone || isFailed;

  const pct =
    data?.total && data.total > 0
      ? Math.min(((data.built ?? 0) / data.total) * 100, 100)
      : 0;

  async function handleRetry() {
    if (!schoolId || !data) return;
    setRetrying(true);
    try {
      const triggered = await triggerSchoolPipeline(schoolId, {
        langs: data.langs,
        force: true,
        year: new Date().getFullYear(),
      });
      router.push(`/school/curriculum/jobs/${triggered.job_id}`);
    } catch {
      setRetrying(false);
    }
  }

  return (
    <div className="max-w-2xl space-y-6 p-6">
      <div className="flex items-center gap-3">
        <LinkButton href="/school/curriculum/jobs" variant="outline" size="sm">
          ← All jobs
        </LinkButton>
        <h1 className="text-2xl font-bold text-gray-900">Job Detail</h1>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
        </div>
      ) : !data ? (
        <p className="text-sm text-gray-500">Job not found.</p>
      ) : (
        <>
          {/* Status card */}
          <Card className="border shadow-sm">
            <CardHeader className="pb-2">
              <div className="flex items-center gap-2">
                <StatusIcon status={data.status} />
                <CardTitle className="text-base capitalize">{data.status}</CardTitle>
              </div>
              <p className="mt-1 font-mono text-xs text-gray-400">{job_id}</p>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Progress bar */}
              {data.total != null && (
                <div>
                  <div className="mb-1 flex justify-between text-xs text-gray-500">
                    <span>
                      {data.built ?? 0} built · {data.failed ?? 0} failed · {data.total}{" "}
                      total
                    </span>
                    <span>{pct.toFixed(0)}%</span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-gray-100">
                    <div
                      className={cn(
                        "h-full rounded-full transition-all duration-500",
                        isFailed && (data.failed ?? 0) > 0 ? "bg-red-400" : "bg-blue-500",
                        isDone && "bg-green-500",
                      )}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              )}

              {isDone && (
                <div className="flex items-center gap-2 rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-700">
                  <CheckCircle className="h-4 w-4 shrink-0" />
                  Content generation complete. {data.built} unit
                  {data.built !== 1 ? "s" : ""} built successfully.
                </div>
              )}

              {isFailed && (
                <div className="space-y-2 rounded-lg border border-red-200 bg-red-50 p-3">
                  <p className="text-sm font-medium text-red-700">
                    Pipeline failed — {data.failed} unit{data.failed !== 1 ? "s" : ""}{" "}
                    could not be generated.
                  </p>
                  {data.error && (
                    <p className="font-mono text-xs text-red-600">{data.error}</p>
                  )}
                  <p className="text-xs text-red-600">
                    {data.built} unit{data.built !== 1 ? "s" : ""} succeeded. Use the
                    Retry button to re-run with force rebuild.
                  </p>
                </div>
              )}

              {isRunning && (
                <p className="animate-pulse text-center text-xs text-gray-400">
                  Refreshing every 5 seconds…
                </p>
              )}
            </CardContent>
          </Card>

          {/* Metadata */}
          <Card className="border shadow-sm">
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Details</CardTitle>
            </CardHeader>
            <CardContent>
              <dl className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
                <div>
                  <dt className="text-xs text-gray-400">Grade</dt>
                  <dd className="font-medium text-gray-800">
                    {data.grade ? `Grade ${data.grade}` : "—"}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-gray-400">Languages</dt>
                  <dd className="font-mono text-xs text-gray-700 uppercase">{data.langs}</dd>
                </div>
                <div>
                  <dt className="text-xs text-gray-400">Curriculum ID</dt>
                  <dd className="font-mono text-xs text-gray-500 break-all">
                    {data.curriculum_id}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-gray-400">Payload size</dt>
                  <dd className="text-gray-700">{fmtBytes(data.payload_bytes)}</dd>
                </div>
                <div>
                  <dt className="text-xs text-gray-400">Triggered</dt>
                  <dd className="text-gray-700">{fmtDate(data.triggered_at)}</dd>
                </div>
                <div>
                  <dt className="text-xs text-gray-400">Started</dt>
                  <dd className="text-gray-700">{fmtDate(data.started_at)}</dd>
                </div>
                <div>
                  <dt className="text-xs text-gray-400">Completed</dt>
                  <dd className="text-gray-700">{fmtDate(data.completed_at)}</dd>
                </div>
                <div>
                  <dt className="text-xs text-gray-400">Duration</dt>
                  <dd className="text-gray-700">
                    {duration(data.started_at, data.completed_at)}
                  </dd>
                </div>
                {data.triggered_by_email && (
                  <div className="col-span-2">
                    <dt className="text-xs text-gray-400">Triggered by</dt>
                    <dd className="text-gray-700">{data.triggered_by_email}</dd>
                  </div>
                )}
              </dl>
            </CardContent>
          </Card>

          {/* Actions */}
          {isFinished && (
            <div className="flex gap-2">
              {isFailed && (
                <Button onClick={handleRetry} disabled={retrying} variant="outline" className="gap-2">
                  {retrying ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <RotateCcw className="h-4 w-4" />
                  )}
                  Retry (force rebuild)
                </Button>
              )}
              <LinkButton href="/school/curriculum">Back to curriculum</LinkButton>
              <LinkButton href="/school/curriculum/jobs" variant="outline">
                All jobs
              </LinkButton>
            </div>
          )}
        </>
      )}
    </div>
  );
}
