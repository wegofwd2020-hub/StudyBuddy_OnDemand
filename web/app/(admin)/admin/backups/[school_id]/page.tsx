"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter, useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, RefreshCw, Plus, Archive } from "lucide-react";
import {
  Backup,
  listSchoolBackups,
  createBackup,
} from "@/lib/api/backup";

const STATUS_STYLES: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-700",
  running: "bg-blue-100 text-blue-700",
  completed: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
};

const MAX_BACKUPS = 10;

function fmtBytes(n: number): string {
  if (n === 0) return "0 B";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  if (n < 1024 * 1024 * 1024) return `${(n / (1024 * 1024)).toFixed(1)} MB`;
  return `${(n / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

function fmtDate(s: string): string {
  return new Date(s).toLocaleString();
}

export default function SchoolBackupsPage() {
  const router = useRouter();
  const params = useParams();
  const schoolId = params.school_id as string;

  const [token, setToken] = useState<string | null>(null);
  const [backups, setBackups] = useState<Backup[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Create modal state
  const [showModal, setShowModal] = useState(false);
  const [modalScopeType, setModalScopeType] = useState<"full" | "grade" | "name">("full");
  const [modalScopeValue, setModalScopeValue] = useState("");
  const [modalLabel, setModalLabel] = useState("");
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  useEffect(() => {
    const t = localStorage.getItem("sb_admin_token");
    if (!t) {
      router.push("/admin/login");
      return;
    }
    setToken(t);
  }, [router]);

  const load = useCallback(async () => {
    if (!token || !schoolId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await listSchoolBackups(schoolId);
      setBackups(data.backups ?? []);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load backups");
    } finally {
      setLoading(false);
    }
  }, [token, schoolId]);

  useEffect(() => {
    load();
  }, [load]);

  // Auto-refresh if any backup is active
  useEffect(() => {
    const hasActive = backups.some(
      (b) => b.status === "running" || b.status === "pending"
    );
    if (!hasActive) return;
    const timer = setInterval(load, 5000);
    return () => clearInterval(timer);
  }, [backups, load]);

  async function handleCreate() {
    setCreating(true);
    setCreateError(null);
    try {
      await createBackup(schoolId, {
        scope_type: modalScopeType,
        scope_value:
          modalScopeType !== "full" && modalScopeValue.trim()
            ? modalScopeValue.trim()
            : undefined,
        label: modalLabel.trim() || undefined,
      });
      setShowModal(false);
      setModalScopeType("full");
      setModalScopeValue("");
      setModalLabel("");
      await load();
    } catch (e: unknown) {
      setCreateError(e instanceof Error ? e.message : "Failed to create backup");
    } finally {
      setCreating(false);
    }
  }

  if (!token) return null;

  const retentionUsed = backups.length;
  const retentionPct = Math.round((retentionUsed / MAX_BACKUPS) * 100);

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="flex items-center gap-2 mb-4">
        <Link
          href="/admin/backups"
          className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700"
        >
          <ArrowLeft className="w-4 h-4" />
          All Backups
        </Link>
      </div>

      <div className="flex items-center justify-between mb-4">
        <div>
          <div className="flex items-center gap-2">
            <Archive className="w-5 h-5 text-gray-600" />
            <h1 className="text-xl font-semibold text-gray-900">
              School Backups
            </h1>
          </div>
          <p className="text-xs text-gray-500 font-mono mt-0.5">{schoolId}</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={load}
            className="flex items-center gap-1 px-3 py-1.5 text-sm border border-gray-300 rounded-md hover:bg-gray-50"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
          <button
            onClick={() => setShowModal(true)}
            className="flex items-center gap-1 px-3 py-1.5 text-sm bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
          >
            <Plus className="w-4 h-4" />
            Create Backup
          </button>
        </div>
      </div>

      {/* Retention indicator */}
      <div className="mb-5 p-3 bg-gray-50 border border-gray-200 rounded-md">
        <div className="flex justify-between text-sm mb-1">
          <span className="font-medium text-gray-700">
            Backup retention: {retentionUsed} of {MAX_BACKUPS} used
          </span>
          <span
            className={
              retentionPct >= 80 ? "text-orange-600 font-medium" : "text-gray-500"
            }
          >
            {retentionPct}%
          </span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div
            className={`h-2 rounded-full transition-all ${
              retentionPct >= 80 ? "bg-orange-500" : "bg-indigo-500"
            }`}
            style={{ width: `${Math.min(retentionPct, 100)}%` }}
          />
        </div>
        {retentionPct >= 80 && (
          <p className="text-xs text-orange-600 mt-1">
            Oldest backups will be pruned automatically when the limit is reached.
          </p>
        )}
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md text-red-700 text-sm">
          {error}
        </div>
      )}

      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading backups…</div>
      ) : backups.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          No backups yet for this school.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="bg-gray-50 text-left">
                <th className="px-4 py-2 font-medium text-gray-700 border-b">Label</th>
                <th className="px-4 py-2 font-medium text-gray-700 border-b">Scope</th>
                <th className="px-4 py-2 font-medium text-gray-700 border-b">Status</th>
                <th className="px-4 py-2 font-medium text-gray-700 border-b">Files</th>
                <th className="px-4 py-2 font-medium text-gray-700 border-b">Size</th>
                <th className="px-4 py-2 font-medium text-gray-700 border-b">Created</th>
              </tr>
            </thead>
            <tbody>
              {backups.map((b) => (
                <tr key={b.id} className="border-b hover:bg-gray-50">
                  <td className="px-4 py-2 text-gray-700">{b.label || "—"}</td>
                  <td className="px-4 py-2 text-gray-700">
                    {b.scope_type}
                    {b.scope_value ? `: ${b.scope_value}` : ""}
                  </td>
                  <td className="px-4 py-2">
                    <span
                      className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${
                        STATUS_STYLES[b.status] ?? "bg-gray-100 text-gray-600"
                      }`}
                    >
                      {b.status}
                    </span>
                  </td>
                  <td className="px-4 py-2 font-mono text-xs text-gray-600">
                    {b.file_count}
                  </td>
                  <td className="px-4 py-2 font-mono text-xs text-gray-600">
                    {fmtBytes(b.total_bytes)}
                  </td>
                  <td className="px-4 py-2 text-xs text-gray-600">
                    {fmtDate(b.created_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Create backup modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md">
            <h2 className="text-lg font-semibold mb-4">Create Backup</h2>

            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Scope
                </label>
                <div className="flex gap-4">
                  {(["full", "grade", "name"] as const).map((s) => (
                    <label key={s} className="flex items-center gap-1 text-sm">
                      <input
                        type="radio"
                        name="scope"
                        value={s}
                        checked={modalScopeType === s}
                        onChange={() => setModalScopeType(s)}
                      />
                      {s}
                    </label>
                  ))}
                </div>
              </div>

              {modalScopeType !== "full" && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    {modalScopeType === "grade" ? "Grade number" : "Curriculum name pattern"}
                  </label>
                  <input
                    type="text"
                    value={modalScopeValue}
                    onChange={(e) => setModalScopeValue(e.target.value)}
                    placeholder={modalScopeType === "grade" ? "8" : "Science"}
                    className="w-full border rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Label (optional)
                </label>
                <input
                  type="text"
                  value={modalLabel}
                  onChange={(e) => setModalLabel(e.target.value)}
                  placeholder="e.g. before migration"
                  className="w-full border rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
            </div>

            {createError && (
              <p className="mt-3 text-sm text-red-600">{createError}</p>
            )}

            <div className="mt-5 flex justify-end gap-2">
              <button
                onClick={() => {
                  setShowModal(false);
                  setCreateError(null);
                }}
                className="px-4 py-2 text-sm border border-gray-300 rounded-md hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleCreate}
                disabled={creating}
                className="px-4 py-2 text-sm bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50"
              >
                {creating ? "Creating…" : "Create Backup"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
