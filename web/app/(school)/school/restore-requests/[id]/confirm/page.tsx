"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTeacher } from "@/lib/hooks/useTeacher";
import {
  schoolGetRestoreRequest,
  schoolConfirmRestore,
  schoolCancelRestoreRequest,
  type RestoreRequest,
} from "@/lib/api/backup";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { AlertCircle, CheckCircle2, XCircle, RotateCcw } from "lucide-react";

// ── Page ───────────────────────────────────────────────────────────────────────

export default function ConfirmRestorePage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const teacher = useTeacher();
  const schoolId = teacher?.school_id ?? "";

  const [sideBySide, setSideBySide] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const { data: request, isLoading } = useQuery<RestoreRequest>({
    queryKey: ["school-restore-request", schoolId, id],
    queryFn: () => schoolGetRestoreRequest(schoolId, id),
    enabled: !!schoolId && !!id,
    staleTime: 10_000,
  });

  const confirmMutation = useMutation({
    mutationFn: () => schoolConfirmRestore(schoolId, id, sideBySide),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["school-restore-requests", schoolId] });
      router.push("/school/restore-requests");
    },
    onError: (err: unknown) => {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Failed to confirm. Please try again.";
      setActionError(msg);
    },
  });

  const cancelMutation = useMutation({
    mutationFn: () => schoolCancelRestoreRequest(schoolId, id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["school-restore-requests", schoolId] });
      router.push("/school/restore-requests");
    },
    onError: (err: unknown) => {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Failed to cancel. Please try again.";
      setActionError(msg);
    },
  });

  const busy = confirmMutation.isPending || cancelMutation.isPending;

  if (isLoading) {
    return (
      <div className="max-w-2xl space-y-4 p-6">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-48 rounded-lg" />
      </div>
    );
  }

  if (!request) {
    return (
      <div className="max-w-2xl p-6">
        <p className="text-sm text-red-600">Restore request not found.</p>
      </div>
    );
  }

  const hasConflicts = !!request.conflict_catalog_id;
  const canConfirm = request.status === "awaiting_school_confirm";
  const canCancel = request.status === "submitted";

  const statusColors: Record<string, string> = {
    completed: "text-green-700",
    failed: "text-red-700",
    cancelled: "text-gray-500",
    awaiting_school_confirm: "text-orange-700 font-semibold",
  };

  return (
    <div className="max-w-2xl space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center gap-2">
        <RotateCcw className="h-6 w-6 text-indigo-600" />
        <h1 className="text-2xl font-bold text-gray-900">Restore Request</h1>
      </div>

      {/* Summary card */}
      <div className="space-y-3 rounded-lg border border-gray-200 bg-white p-5">
        <h2 className="text-sm font-semibold tracking-wide text-gray-700 uppercase">
          Request summary
        </h2>
        <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
          <dt className="text-gray-500">Status</dt>
          <dd className={statusColors[request.status] ?? "text-gray-900"}>
            {request.status.replace(/_/g, " ")}
          </dd>

          <dt className="text-gray-500">Scope</dt>
          <dd className="text-gray-900 capitalize">
            {request.scope_type === "full"
              ? "Full restore"
              : request.scope_type === "grade"
                ? `Grade ${request.scope_value}`
                : (request.scope_value ?? request.scope_type)}
          </dd>

          <dt className="text-gray-500">Side-by-side</dt>
          <dd className="text-gray-900">{request.side_by_side ? "Yes" : "No"}</dd>

          <dt className="text-gray-500">Submitted</dt>
          <dd className="text-gray-900 tabular-nums">
            {new Date(request.created_at).toLocaleString()}
          </dd>

          {request.scheduled_at && (
            <>
              <dt className="text-gray-500">Preferred time</dt>
              <dd className="text-gray-900 tabular-nums">
                {new Date(request.scheduled_at).toLocaleString()}
                <span className="ml-1 text-xs font-normal text-gray-400">
                  (an administrator will action this manually — not automatic)
                </span>
              </dd>
            </>
          )}

          {request.notes && (
            <>
              <dt className="text-gray-500">Notes</dt>
              <dd className="text-gray-900">{request.notes}</dd>
            </>
          )}
        </dl>
      </div>

      {/* Conflicts section */}
      {canConfirm && (
        <div
          className={`space-y-4 rounded-lg border p-5 ${
            hasConflicts ? "border-orange-200 bg-orange-50" : "border-blue-200 bg-blue-50"
          }`}
        >
          <div className="flex items-start gap-3">
            {hasConflicts ? (
              <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-orange-600" />
            ) : (
              <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-blue-600" />
            )}
            <div>
              <p
                className={`text-sm font-semibold ${
                  hasConflicts ? "text-orange-800" : "text-blue-800"
                }`}
              >
                {hasConflicts
                  ? "Conflicts detected — your confirmation is required"
                  : "No conflicts detected — ready to restore"}
              </p>
              <p
                className={`mt-1 text-xs ${
                  hasConflicts ? "text-orange-700" : "text-blue-700"
                }`}
              >
                {hasConflicts
                  ? "Some curriculum content has been modified since the backup was taken. " +
                    "Confirming will overwrite those changes. The conflicting content has been " +
                    "staged in a temporary catalog for you to review."
                  : "The administrator has verified that no content has been modified since the " +
                    "backup. Confirming will restore the content immediately."}
              </p>
            </div>
          </div>

          {/* Side-by-side toggle */}
          <label className="flex cursor-pointer items-start gap-3 rounded-lg border border-white/60 bg-white/60 p-3">
            <input
              type="checkbox"
              checked={sideBySide}
              onChange={(e) => setSideBySide(e.target.checked)}
              className="mt-0.5"
            />
            <div>
              <p className="text-sm font-medium text-gray-900">Side-by-side restore</p>
              <p className="text-xs text-gray-500">
                Restore to a new versioned catalog (
                <code className="text-xs">{"{name}.{yyyymmdd}"}</code>) instead of
                overwriting the live curriculum. Recommended if you want to compare first.
              </p>
            </div>
          </label>

          {/* Action buttons */}
          {actionError && (
            <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {actionError}
            </p>
          )}

          <div className="flex items-center gap-3">
            <Button
              onClick={() => confirmMutation.mutate()}
              disabled={busy}
              className="bg-indigo-600 text-white hover:bg-indigo-700"
            >
              <CheckCircle2 className="mr-1.5 h-4 w-4" />
              {confirmMutation.isPending ? "Confirming…" : "Confirm restore"}
            </Button>
            <Button
              variant="outline"
              onClick={() => router.push("/school/restore-requests")}
              disabled={busy}
            >
              Decide later
            </Button>
          </div>
        </div>
      )}

      {/* Cancel option for submitted requests */}
      {canCancel && (
        <div className="space-y-3 rounded-lg border border-gray-200 bg-white p-5">
          <p className="text-sm text-gray-600">
            Your request has been submitted and is awaiting review by the administrator.
          </p>
          {actionError && (
            <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {actionError}
            </p>
          )}
          <Button
            variant="outline"
            onClick={() => cancelMutation.mutate()}
            disabled={busy}
            className="border-red-200 text-red-600 hover:bg-red-50"
          >
            <XCircle className="mr-1.5 h-4 w-4" />
            {cancelMutation.isPending ? "Cancelling…" : "Cancel this request"}
          </Button>
        </div>
      )}

      {/* Terminal states */}
      {request.status === "completed" && (
        <div className="flex items-center gap-3 rounded-lg border border-green-200 bg-green-50 p-4">
          <CheckCircle2 className="h-5 w-5 text-green-600" />
          <p className="text-sm font-medium text-green-800">
            Restore completed successfully.
          </p>
        </div>
      )}

      {request.status === "failed" && (
        <div className="flex items-center gap-3 rounded-lg border border-red-200 bg-red-50 p-4">
          <XCircle className="h-5 w-5 text-red-600" />
          <p className="text-sm font-medium text-red-800">
            Restore failed. Contact your administrator for details.
          </p>
        </div>
      )}

      <div>
        <button
          type="button"
          onClick={() => router.push("/school/restore-requests")}
          className="text-sm text-indigo-600 hover:underline"
        >
          ← Back to restore requests
        </button>
      </div>
    </div>
  );
}
