"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, RotateCcw } from "lucide-react";
import {
  RestoreRequest,
  acknowledgeRestoreRequest,
  executeRestoreRequest,
  cancelRestoreRequest,
} from "@/lib/api/backup";
import adminClient from "@/lib/api/admin-client";
import { describeSchedule } from "@/lib/school/restore-schedule";

const STATUS_STYLES: Record<string, string> = {
  submitted: "bg-yellow-100 text-yellow-700",
  acknowledged: "bg-blue-100 text-blue-700",
  dry_run: "bg-blue-100 text-blue-700",
  awaiting_school_confirm: "bg-orange-100 text-orange-700",
  in_progress: "bg-indigo-100 text-indigo-700",
  completed: "bg-green-100 text-green-700",
  cancelled: "bg-red-100 text-red-600",
  failed: "bg-red-100 text-red-700",
};

function fmtDate(s: string | null): string {
  if (!s) return "—";
  return new Date(s).toLocaleString();
}

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex gap-2 border-b py-2 last:border-b-0">
      <span className="w-40 flex-shrink-0 text-sm font-medium text-gray-600">
        {label}
      </span>
      <span className="text-sm break-all text-gray-900">{value ?? "—"}</span>
    </div>
  );
}

export default function RestoreRequestDetailPage() {
  const router = useRouter();
  const params = useParams();
  const requestId = params.id as string;

  const [token, setToken] = useState<string | null>(null);
  const [request, setRequest] = useState<RestoreRequest | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    const t = localStorage.getItem("sb_admin_token");
    if (!t) {
      router.push("/admin/login");
      return;
    }
    setToken(t);
  }, [router]);

  async function load() {
    if (!token || !requestId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await adminClient.get(`/admin/restore-requests`).then((r) => r.data);
      const found = (data.requests as RestoreRequest[]).find((r) => r.id === requestId);
      if (!found) {
        setError("Restore request not found");
      } else {
        setRequest(found);
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load request");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (token) load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, requestId]);

  async function handleAcknowledge() {
    setActionLoading("ack");
    setActionError(null);
    try {
      await acknowledgeRestoreRequest(requestId);
      await load();
    } catch (e: unknown) {
      setActionError(e instanceof Error ? e.message : "Action failed");
    } finally {
      setActionLoading(null);
    }
  }

  async function handleExecute() {
    setActionLoading("exec");
    setActionError(null);
    try {
      await executeRestoreRequest(requestId);
      await load();
    } catch (e: unknown) {
      setActionError(e instanceof Error ? e.message : "Action failed");
    } finally {
      setActionLoading(null);
    }
  }

  async function handleCancel() {
    setActionLoading("cancel");
    setActionError(null);
    try {
      await cancelRestoreRequest(requestId);
      await load();
    } catch (e: unknown) {
      setActionError(e instanceof Error ? e.message : "Action failed");
    } finally {
      setActionLoading(null);
    }
  }

  if (!token) return null;

  return (
    <div className="mx-auto max-w-3xl p-6">
      <div className="mb-4 flex items-center gap-2">
        <Link
          href="/admin/restore-requests"
          className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700"
        >
          <ArrowLeft className="h-4 w-4" />
          Restore Requests
        </Link>
      </div>

      <div className="mb-6 flex items-center gap-2">
        <RotateCcw className="h-5 w-5 text-gray-600" />
        <h1 className="text-xl font-semibold text-gray-900">Restore Request Detail</h1>
      </div>

      {error && (
        <div className="mb-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}
      {actionError && (
        <div className="mb-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {actionError}
        </div>
      )}

      {loading ? (
        <div className="py-12 text-center text-gray-500">Loading…</div>
      ) : !request ? (
        <div className="py-12 text-center text-gray-500">Request not found.</div>
      ) : (
        <>
          {/* Status banner */}
          <div className="mb-6 flex items-center gap-3 rounded-lg border border-gray-200 bg-gray-50 p-4">
            <span
              className={`inline-block rounded-full px-3 py-1 text-sm font-semibold ${
                STATUS_STYLES[request.status] ?? "bg-gray-100 text-gray-600"
              }`}
            >
              {request.status}
            </span>
            <span className="text-sm text-gray-500">
              Last updated: {fmtDate(request.updated_at)}
            </span>
          </div>

          {/* Detail fields */}
          <div className="mb-6 rounded-lg border border-gray-200 bg-white p-4">
            <Field
              label="Request ID"
              value={<span className="font-mono text-xs">{request.id}</span>}
            />
            <Field
              label="School ID"
              value={<span className="font-mono text-xs">{request.school_id}</span>}
            />
            <Field
              label="Backup ID"
              value={
                request.backup_id ? (
                  <span className="font-mono text-xs">{request.backup_id}</span>
                ) : (
                  "—"
                )
              }
            />
            <Field
              label="Scope"
              value={`${request.scope_type}${request.scope_value ? `: ${request.scope_value}` : ""}`}
            />
            <Field label="Side-by-side" value={request.side_by_side ? "Yes" : "No"} />
            <Field
              label="Conflict catalog"
              value={
                request.conflict_catalog_id ? (
                  <span className="font-mono text-xs">{request.conflict_catalog_id}</span>
                ) : (
                  "None"
                )
              }
            />
            <Field label="Notes" value={request.notes || "—"} />
            <Field
              label="Preferred time"
              value={
                request.scheduled_at ? (
                  <>
                    {fmtDate(request.scheduled_at)}{" "}
                    {describeSchedule(request.scheduled_at, request.status).kind ===
                    "unschedulable" ? (
                      <span className="text-xs font-normal text-amber-700">
                        (outside the 30-day window — not automatic; action it below)
                      </span>
                    ) : (
                      <span className="text-xs font-normal text-gray-400">
                        (school-requested — not automatic; action it below)
                      </span>
                    )}
                  </>
                ) : (
                  "— (ASAP)"
                )
              }
            />
            <Field label="Submitted" value={fmtDate(request.created_at)} />
          </div>

          {/* Actions */}
          <div className="flex flex-wrap gap-2">
            {request.status === "submitted" && (
              <button
                onClick={handleAcknowledge}
                disabled={actionLoading === "ack"}
                className="rounded-md bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {actionLoading === "ack" ? "Acknowledging…" : "Acknowledge"}
              </button>
            )}
            {["acknowledged", "awaiting_school_confirm"].includes(request.status) && (
              <button
                onClick={handleExecute}
                disabled={actionLoading === "exec"}
                className="rounded-md bg-indigo-600 px-4 py-2 text-sm text-white hover:bg-indigo-700 disabled:opacity-50"
              >
                {actionLoading === "exec" ? "Dispatching…" : "Execute Restore"}
              </button>
            )}
            {!["completed", "failed", "cancelled"].includes(request.status) && (
              <button
                onClick={handleCancel}
                disabled={actionLoading === "cancel"}
                className="rounded-md bg-red-600 px-4 py-2 text-sm text-white hover:bg-red-700 disabled:opacity-50"
              >
                {actionLoading === "cancel" ? "Cancelling…" : "Cancel"}
              </button>
            )}
          </div>
        </>
      )}
    </div>
  );
}
