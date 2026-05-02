"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { RefreshCw, RotateCcw } from "lucide-react";
import {
  RestoreRequest,
  listAllRestoreRequests,
  acknowledgeRestoreRequest,
  executeRestoreRequest,
  cancelRestoreRequest,
} from "@/lib/api/backup";

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

function fmtDate(s: string): string {
  return new Date(s).toLocaleString();
}

export default function RestoreRequestsPage() {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [requests, setRequests] = useState<RestoreRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  useEffect(() => {
    const t = localStorage.getItem("sb_admin_token");
    if (!t) {
      router.push("/admin/login");
      return;
    }
    setToken(t);
  }, [router]);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const data = await listAllRestoreRequests();
      setRequests(data.requests ?? []);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load restore requests");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleAcknowledge(id: string) {
    setActionLoading(id + ":ack");
    setActionError(null);
    try {
      await acknowledgeRestoreRequest(id);
      await load();
    } catch (e: unknown) {
      setActionError(e instanceof Error ? e.message : "Action failed");
    } finally {
      setActionLoading(null);
    }
  }

  async function handleExecute(id: string) {
    setActionLoading(id + ":exec");
    setActionError(null);
    try {
      await executeRestoreRequest(id);
      await load();
    } catch (e: unknown) {
      setActionError(e instanceof Error ? e.message : "Action failed");
    } finally {
      setActionLoading(null);
    }
  }

  async function handleCancel(id: string) {
    setActionLoading(id + ":cancel");
    setActionError(null);
    try {
      await cancelRestoreRequest(id);
      await load();
    } catch (e: unknown) {
      setActionError(e instanceof Error ? e.message : "Action failed");
    } finally {
      setActionLoading(null);
    }
  }

  if (!token) return null;

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <RotateCcw className="w-5 h-5 text-gray-600" />
          <h1 className="text-xl font-semibold text-gray-900">
            Restore Requests
          </h1>
          <span className="text-sm text-gray-500 ml-2">
            ({requests.length} total)
          </span>
        </div>
        <button
          onClick={load}
          className="flex items-center gap-1 px-3 py-1.5 text-sm border border-gray-300 rounded-md hover:bg-gray-50"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md text-red-700 text-sm">
          {error}
        </div>
      )}
      {actionError && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md text-red-700 text-sm">
          {actionError}
        </div>
      )}

      {loading ? (
        <div className="text-center py-12 text-gray-500">
          Loading restore requests…
        </div>
      ) : requests.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          No restore requests found.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="bg-gray-50 text-left">
                <th className="px-4 py-2 font-medium text-gray-700 border-b">School</th>
                <th className="px-4 py-2 font-medium text-gray-700 border-b">Backup ID</th>
                <th className="px-4 py-2 font-medium text-gray-700 border-b">Scope</th>
                <th className="px-4 py-2 font-medium text-gray-700 border-b">Status</th>
                <th className="px-4 py-2 font-medium text-gray-700 border-b">Submitted</th>
                <th className="px-4 py-2 font-medium text-gray-700 border-b">Actions</th>
              </tr>
            </thead>
            <tbody>
              {requests.map((req) => (
                <tr key={req.id} className="border-b hover:bg-gray-50">
                  <td className="px-4 py-2 font-mono text-xs text-gray-600">
                    {req.school_id.slice(0, 8)}…
                  </td>
                  <td className="px-4 py-2 font-mono text-xs text-gray-600">
                    {req.backup_id ? `${req.backup_id.slice(0, 8)}…` : "—"}
                  </td>
                  <td className="px-4 py-2 text-gray-700">
                    {req.scope_type}
                    {req.scope_value ? `: ${req.scope_value}` : ""}
                  </td>
                  <td className="px-4 py-2">
                    <span
                      className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${
                        STATUS_STYLES[req.status] ?? "bg-gray-100 text-gray-600"
                      }`}
                    >
                      {req.status}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-xs text-gray-600">
                    {fmtDate(req.created_at)}
                  </td>
                  <td className="px-4 py-2">
                    <div className="flex gap-1 flex-wrap">
                      <Link
                        href={`/admin/restore-requests/${req.id}`}
                        className="px-2 py-1 text-xs border border-gray-300 rounded hover:bg-gray-50"
                      >
                        Detail
                      </Link>
                      {req.status === "submitted" && (
                        <button
                          onClick={() => handleAcknowledge(req.id)}
                          disabled={actionLoading === req.id + ":ack"}
                          className="px-2 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
                        >
                          {actionLoading === req.id + ":ack" ? "…" : "Acknowledge"}
                        </button>
                      )}
                      {req.status === "awaiting_school_confirm" && (
                        <button
                          onClick={() => handleExecute(req.id)}
                          disabled={actionLoading === req.id + ":exec"}
                          className="px-2 py-1 text-xs bg-indigo-600 text-white rounded hover:bg-indigo-700 disabled:opacity-50"
                        >
                          {actionLoading === req.id + ":exec" ? "…" : "Execute"}
                        </button>
                      )}
                      {!["completed", "failed", "cancelled"].includes(req.status) && (
                        <button
                          onClick={() => handleCancel(req.id)}
                          disabled={actionLoading === req.id + ":cancel"}
                          className="px-2 py-1 text-xs bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50"
                        >
                          {actionLoading === req.id + ":cancel" ? "…" : "Cancel"}
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
