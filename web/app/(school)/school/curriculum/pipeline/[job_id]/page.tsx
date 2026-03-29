"use client";

import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { getPipelineStatus } from "@/lib/api/curriculum-admin";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { LinkButton } from "@/components/ui/link-button";
import { CheckCircle, XCircle, Loader2, Clock } from "lucide-react";
import { cn } from "@/lib/utils";

function StatusIcon({ status }: { status: string }) {
  if (status === "done") return <CheckCircle className="h-5 w-5 text-green-500" />;
  if (status === "failed") return <XCircle className="h-5 w-5 text-red-500" />;
  if (status === "running")
    return <Loader2 className="h-5 w-5 animate-spin text-blue-500" />;
  return <Clock className="h-5 w-5 text-gray-400" />;
}

export default function PipelineStatusPage() {
  const { job_id } = useParams<{ job_id: string }>();

  const { data, isLoading } = useQuery({
    queryKey: ["pipeline-status", job_id],
    queryFn: () => getPipelineStatus(job_id),
    enabled: !!job_id,
    // Poll every 5 s while job is still running
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "done" || status === "failed") return false;
      return 5_000;
    },
    staleTime: 0,
  });

  const isDone = data?.status === "done";
  const isFailed = data?.status === "failed";
  const isFinished = isDone || isFailed;

  return (
    <div className="max-w-2xl space-y-6 p-6">
      <div className="flex items-center gap-3">
        <LinkButton href="/school/curriculum" variant="outline" size="sm">
          ← Curriculum
        </LinkButton>
        <h1 className="text-2xl font-bold text-gray-900">Pipeline Status</h1>
      </div>

      <Card className="border shadow-sm">
        <CardHeader className="pb-2">
          <div className="flex items-center gap-2">
            {data && <StatusIcon status={data.status} />}
            <CardTitle className="text-base">
              {isLoading ? "Loading…" : (data?.status ?? "Unknown")}
            </CardTitle>
          </div>
          <p className="mt-1 font-mono text-xs text-gray-400">{job_id}</p>
        </CardHeader>
        <CardContent className="space-y-4">
          {data && (
            <>
              {/* Progress bar */}
              <div>
                <div className="mb-1 flex justify-between text-xs text-gray-500">
                  <span>
                    {data.built} built · {data.failed} failed · {data.total} total
                  </span>
                  <span>{data.progress_pct.toFixed(0)}%</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-gray-100">
                  <div
                    className={cn(
                      "h-full rounded-full transition-all duration-500",
                      isFailed && data.failed > 0 ? "bg-red-400" : "bg-blue-500",
                      isDone && "bg-green-500",
                    )}
                    style={{ width: `${data.progress_pct}%` }}
                  />
                </div>
              </div>

              {/* Status messages */}
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
                  <p className="text-xs text-red-600">
                    {data.built} unit{data.built !== 1 ? "s" : ""} succeeded before the
                    failure. You can re-trigger the pipeline from the Curriculum page.
                  </p>
                </div>
              )}

              {!isFinished && (
                <p className="animate-pulse text-center text-xs text-gray-400">
                  Refreshing every 5 seconds…
                </p>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {isFinished && (
        <div className="flex gap-2">
          <LinkButton href="/school/curriculum">Back to curriculum</LinkButton>
          <LinkButton href="/school/dashboard" variant="outline">
            Dashboard
          </LinkButton>
        </div>
      )}
    </div>
  );
}
