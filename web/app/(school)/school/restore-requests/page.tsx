"use client";

import { useQuery } from "@tanstack/react-query";
import { useTeacher } from "@/lib/hooks/useTeacher";
import { schoolListRestoreRequests, type RestoreRequest } from "@/lib/api/backup";
import { Skeleton } from "@/components/ui/skeleton";
import { LinkButton } from "@/components/ui/link-button";
import { RotateCcw, AlertCircle } from "lucide-react";

// ── Helpers ───────────────────────────────────────────────────────────────────

function scopeLabel(r: RestoreRequest): string {
  if (r.scope_type === "full") return "Full restore";
  if (r.scope_type === "grade") return `Grade ${r.scope_value}`;
  return r.scope_value ?? r.scope_type;
}

const STATUS_STYLE: Record<string, string> = {
  submitted: "bg-blue-50 text-blue-700 border-blue-200",
  acknowledged: "bg-yellow-50 text-yellow-700 border-yellow-200",
  dry_run: "bg-yellow-50 text-yellow-700 border-yellow-200",
  awaiting_school_confirm: "bg-orange-50 text-orange-700 border-orange-200",
  in_progress: "bg-blue-50 text-blue-700 border-blue-200",
  completed: "bg-green-50 text-green-700 border-green-200",
  cancelled: "bg-gray-50 text-gray-500 border-gray-200",
  failed: "bg-red-50 text-red-700 border-red-200",
};

const STATUS_LABEL: Record<string, string> = {
  submitted: "Submitted",
  acknowledged: "Acknowledged",
  dry_run: "Checking conflicts…",
  awaiting_school_confirm: "Your confirmation needed",
  in_progress: "Restoring…",
  completed: "Completed",
  cancelled: "Cancelled",
  failed: "Failed",
};

function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium ${STATUS_STYLE[status] ?? "border-gray-200 bg-gray-50 text-gray-600"}`}
    >
      {status === "awaiting_school_confirm" && <AlertCircle className="h-3 w-3" />}
      {STATUS_LABEL[status] ?? status}
    </span>
  );
}

// ── Page ───────────────────────────────────────────────────────────────────────

export default function RestoreRequestsPage() {
  const teacher = useTeacher();
  const schoolId = teacher?.school_id ?? "";
  const isAdmin = teacher?.role === "school_admin";

  const { data, isLoading } = useQuery({
    queryKey: ["school-restore-requests", schoolId],
    queryFn: () => schoolListRestoreRequests(schoolId),
    enabled: !!schoolId,
    staleTime: 15_000,
    refetchInterval: (query) => {
      const reqs: RestoreRequest[] = query.state.data?.requests ?? [];
      const active = ["submitted", "acknowledged", "dry_run", "in_progress"];
      return reqs.some((r) => active.includes(r.status)) ? 10_000 : false;
    },
  });

  const requests: RestoreRequest[] = data?.requests ?? [];
  const needsAction = requests.filter((r) => r.status === "awaiting_school_confirm");

  return (
    <div className="max-w-4xl space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <RotateCcw className="h-6 w-6 text-indigo-600" />
          <h1 className="text-2xl font-bold text-gray-900">Restore Requests</h1>
        </div>
        {isAdmin && (
          <LinkButton href="/school/restore-requests/new" size="sm">
            + New request
          </LinkButton>
        )}
      </div>

      {/* Action-required banner */}
      {needsAction.length > 0 && (
        <div className="flex items-start gap-3 rounded-lg border border-orange-200 bg-orange-50 p-4">
          <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-orange-600" />
          <div className="flex-1">
            <p className="text-sm font-medium text-orange-800">
              {needsAction.length === 1
                ? "1 restore request requires your confirmation"
                : `${needsAction.length} restore requests require your confirmation`}
            </p>
            <p className="mt-0.5 text-xs text-orange-700">
              The platform administrator has reviewed the request and found conflicts.
              Please review and confirm whether to proceed.
            </p>
          </div>
          <LinkButton
            href={`/school/restore-requests/${needsAction[0].id}/confirm`}
            size="sm"
            className="shrink-0 bg-orange-600 text-white hover:bg-orange-700"
          >
            Review
          </LinkButton>
        </div>
      )}

      {/* List */}
      {isLoading ? (
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-12 rounded-lg" />
          ))}
        </div>
      ) : requests.length === 0 ? (
        <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed border-gray-200 py-12 text-center">
          <RotateCcw className="h-8 w-8 text-gray-300" />
          <p className="text-sm font-medium text-gray-500">No restore requests yet</p>
          {isAdmin && (
            <LinkButton href="/school/restore-requests/new" size="sm" className="mt-2">
              Submit a restore request
            </LinkButton>
          )}
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg border border-gray-200">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-semibold text-gray-700">
                  Submitted
                </th>
                <th className="px-4 py-3 text-left font-semibold text-gray-700">Scope</th>
                <th className="px-4 py-3 text-left font-semibold text-gray-700">
                  Status
                </th>
                <th className="px-4 py-3 text-left font-semibold text-gray-700">
                  Preferred time
                </th>
                <th className="px-4 py-3 text-left font-semibold text-gray-700">Notes</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {requests.map((r) => (
                <tr
                  key={r.id}
                  className={`hover:bg-gray-50 ${r.status === "awaiting_school_confirm" ? "bg-orange-50/40" : ""}`}
                >
                  <td className="px-4 py-3 text-gray-600 tabular-nums">
                    {new Date(r.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3 text-gray-900">{scopeLabel(r)}</td>
                  <td className="px-4 py-3">
                    <StatusBadge status={r.status} />
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-500 tabular-nums">
                    {r.scheduled_at ? (
                      <>
                        {new Date(r.scheduled_at).toLocaleString()}
                        {!["completed", "failed", "cancelled"].includes(r.status) && (
                          <div className="text-gray-400">awaiting admin action</div>
                        )}
                      </>
                    ) : (
                      "ASAP"
                    )}
                  </td>
                  <td className="max-w-xs truncate px-4 py-3 text-xs text-gray-500">
                    {r.notes ?? "—"}
                  </td>
                  <td className="px-4 py-3 text-right">
                    {r.status === "awaiting_school_confirm" && (
                      <LinkButton
                        href={`/school/restore-requests/${r.id}/confirm`}
                        size="sm"
                        className="bg-orange-600 text-white hover:bg-orange-700"
                      >
                        Confirm
                      </LinkButton>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="text-xs text-gray-400">
        Restore requests are reviewed and executed by the platform administrator. You will
        be notified by email at each stage.
      </p>
    </div>
  );
}
