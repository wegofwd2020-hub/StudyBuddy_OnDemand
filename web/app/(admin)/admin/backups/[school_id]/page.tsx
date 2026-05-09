"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter, useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, RefreshCw, Plus, Archive } from "lucide-react";
import { Backup, listSchoolBackups, createBackup } from "@/lib/api/backup";

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
      (b) => b.status === "running" || b.status === "pending",
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
    <div className="mx-auto max-w-5xl p-6">
      <div className="mb-4 flex items-center gap-2">
        <Link
          href="/admin/backups"
          className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700"
        >
          <ArrowLeft className="h-4 w-4" />
          All Backups
        </Link>
      </div>

      <div className="mb-4 flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <Archive className="h-5 w-5 text-gray-600" />
            <h1 className="text-xl font-semibold text-gray-900">School Backups</h1>
          </div>
          <p className="mt-0.5 font-mono text-xs text-gray-500">{schoolId}</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={load}
            className="flex items-center gap-1 rounded-md border border-gray-300 px-3 py-1.5 text-sm hover:bg-gray-50"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
          <button
            onClick={() => setShowModal(true)}
            className="flex items-center gap-1 rounded-md bg-indigo-600 px-3 py-1.5 text-sm text-white hover:bg-indigo-700"
          >
            <Plus className="h-4 w-4" />
            Create Backup
          </button>
        </div>
      </div>

      {/* Retention indicator */}
      <div className="mb-5 rounded-md border border-gray-200 bg-gray-50 p-3">
        <div className="mb-1 flex justify-between text-sm">
          <span className="font-medium text-gray-700">
            Backup retention: {retentionUsed} of {MAX_BACKUPS} used
          </span>
          <span
            className={
              retentionPct >= 80 ? "font-medium text-orange-600" : "text-gray-500"
            }
          >
            {retentionPct}%
          </span>
        </div>
        <div className="h-2 w-full rounded-full bg-gray-200">
          <div
            className={`h-2 rounded-full transition-all ${
              retentionPct >= 80 ? "bg-orange-500" : "bg-indigo-500"
            }`}
            style={{ width: `${Math.min(retentionPct, 100)}%` }}
          />
        </div>
        {retentionPct >= 80 && (
          <p className="mt-1 text-xs text-orange-600">
            Oldest backups will be pruned automatically when the limit is reached.
          </p>
        )}
      </div>

      {error && (
        <div className="mb-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {loading ? (
        <div className="py-12 text-center text-gray-500">Loading backups…</div>
      ) : backups.length === 0 ? (
        <div className="py-12 text-center text-gray-500">
          No backups yet for this school.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="bg-gray-50 text-left">
                <th className="border-b px-4 py-2 font-medium text-gray-700">Label</th>
                <th className="border-b px-4 py-2 font-medium text-gray-700">Scope</th>
                <th className="border-b px-4 py-2 font-medium text-gray-700">Status</th>
                <th className="border-b px-4 py-2 font-medium text-gray-700">Files</th>
                <th className="border-b px-4 py-2 font-medium text-gray-700">Size</th>
                <th className="border-b px-4 py-2 font-medium text-gray-700">Created</th>
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
                      className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
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
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
            <h2 className="mb-4 text-lg font-semibold">Create Backup</h2>

            <div className="space-y-3">
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">
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
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    {modalScopeType === "grade"
                      ? "Grade number"
                      : "Curriculum name pattern"}
                  </label>
                  <input
                    type="text"
                    value={modalScopeValue}
                    onChange={(e) => setModalScopeValue(e.target.value)}
                    placeholder={modalScopeType === "grade" ? "8" : "Science"}
                    className="w-full rounded-md border px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                  />
                </div>
              )}

              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">
                  Label (optional)
                </label>
                <input
                  type="text"
                  value={modalLabel}
                  onChange={(e) => setModalLabel(e.target.value)}
                  placeholder="e.g. before migration"
                  className="w-full rounded-md border px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                />
              </div>
            </div>

            {createError && <p className="mt-3 text-sm text-red-600">{createError}</p>}

            <div className="mt-5 flex justify-end gap-2">
              <button
                onClick={() => {
                  setShowModal(false);
                  setCreateError(null);
                }}
                className="rounded-md border border-gray-300 px-4 py-2 text-sm hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleCreate}
                disabled={creating}
                className="rounded-md bg-indigo-600 px-4 py-2 text-sm text-white hover:bg-indigo-700 disabled:opacity-50"
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
