"use client";

import { useQuery } from "@tanstack/react-query";
import { getSystemHealth, type ServiceStatus } from "@/lib/api/admin";
import { cn } from "@/lib/utils";
import { CheckCircle, XCircle, RefreshCw } from "lucide-react";

function StatusBadge({ status }: { status: ServiceStatus }) {
  const ok = status === "ok";
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-sm font-medium",
        ok ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700",
      )}
    >
      {ok ? <CheckCircle className="h-3.5 w-3.5" /> : <XCircle className="h-3.5 w-3.5" />}
      {status}
    </span>
  );
}

function ServiceRow({
  name,
  status,
  meta,
}: {
  name: string;
  status: ServiceStatus;
  meta?: string;
}) {
  return (
    <div className="flex items-center justify-between border-b border-gray-100 py-4 last:border-0">
      <div>
        <p className="text-sm font-medium text-gray-900">{name}</p>
        {meta && <p className="mt-0.5 text-xs text-gray-400">{meta}</p>}
      </div>
      <StatusBadge status={status} />
    </div>
  );
}

export default function AdminHealthPage() {
  const { data, isLoading, dataUpdatedAt } = useQuery({
    queryKey: ["admin", "health"],
    queryFn: getSystemHealth,
    staleTime: 0,
    refetchInterval: 10_000,
  });

  const overallOk = data?.db_status === "ok" && data?.redis_status === "ok";

  return (
    <div className="mx-auto max-w-2xl p-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">System Health</h1>
          <p className="mt-0.5 text-sm text-gray-500">Auto-refreshes every 10 seconds</p>
        </div>
        {!isLoading && (
          <div className="flex items-center gap-2 text-xs text-gray-400">
            <RefreshCw className="h-3.5 w-3.5" />
            <span>
              Last checked{" "}
              {dataUpdatedAt ? new Date(dataUpdatedAt).toLocaleTimeString() : "—"}
            </span>
          </div>
        )}
      </div>

      {/* Overall status banner */}
      {!isLoading && data && (
        <div
          className={cn(
            "mb-8 flex items-center gap-3 rounded-xl p-4",
            overallOk
              ? "border border-green-200 bg-green-50"
              : "border border-red-200 bg-red-50",
          )}
        >
          {overallOk ? (
            <CheckCircle className="h-5 w-5 text-green-600" />
          ) : (
            <XCircle className="h-5 w-5 text-red-600" />
          )}
          <span
            className={cn(
              "text-sm font-semibold",
              overallOk ? "text-green-800" : "text-red-800",
            )}
          >
            {overallOk ? "All systems operational" : "One or more systems degraded"}
          </span>
        </div>
      )}

      {isLoading ? (
        <div className="h-48 animate-pulse rounded-xl bg-gray-100" />
      ) : data ? (
        <div className="rounded-xl border border-gray-200 bg-white px-6">
          <ServiceRow
            name="PostgreSQL"
            status={data.db_status}
            meta={
              data.db_pool_size !== undefined
                ? `Pool: ${data.db_pool_available ?? "?"}/${data.db_pool_size} available`
                : undefined
            }
          />
          <ServiceRow
            name="Redis"
            status={data.redis_status}
            meta={
              data.redis_connected_clients !== undefined
                ? `${data.redis_connected_clients} connected clients`
                : undefined
            }
          />
        </div>
      ) : (
        <p className="text-sm text-gray-400">Health check unavailable.</p>
      )}
    </div>
  );
}
