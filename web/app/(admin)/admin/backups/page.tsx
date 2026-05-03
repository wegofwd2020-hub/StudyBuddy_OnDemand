"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { RefreshCw, Plus, Archive } from "lucide-react";
import {
  Backup,
  listAllBackups,
  createBackup,
} from "@/lib/api/backup";

const STATUS_STYLES: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-700",
  running: "bg-blue-100 text-blue-700",
  completed: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
};

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

export default function BackupsPage() {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [backups, setBackups] = useState<Backup[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Create backup modal state
  const [showModal, setShowModal] = useState(false);
  const [modalSchoolId, setModalSchoolId] = useState("");
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
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const data = await listAllBackups(page, 20);
      setBackups(data.backups ?? []);
      setTotal(data.total ?? 0);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load backups");
    } finally {
      setLoading(false);
    }
  }, [token, page]);

  useEffect(() => {
    load();
  }, [load]);

  // Auto-refresh every 5s if any backup is running/pending
  useEffect(() => {
    const hasActive = backups.some(
      (b) => b.status === "running" || b.status === "pending"
    );
    if (!hasActive) return;
    const timer = setInterval(load, 5000);
    return () => clearInterval(timer);
  }, [backups, load]);

  async function handleCreate() {
    if (!modalSchoolId.trim()) {
      setCreateError("School ID is required");
      return;
    }
    setCreating(true);
    setCreateError(null);
    try {
      await createBackup(modalSchoolId.trim(), {
        scope_type: modalScopeType,
        scope_value:
          modalScopeType !== "full" && modalScopeValue.trim()
            ? modalScopeValue.trim()
            : undefined,
        label: modalLabel.trim() || undefined,
      });
      setShowModal(false);
      setModalSchoolId("");
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

  const perPage = 20;
  const totalPages = Math.max(1, Math.ceil(total / perPage));

  if (!token) return null;

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <Archive className="w-5 h-5 text-gray-600" />
          <h1 className="text-xl font-semibold text-gray-900">
            Curriculum Backups
          </h1>
          <span className="text-sm text-gray-500 ml-2">({total} total)</span>
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

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md text-red-700 text-sm">
          {error}
        </div>
      )}

      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading backups…</div>
      ) : backups.length === 0 ? (
        <div className="text-center py-12 text-gray-500">No backups found.</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="bg-gray-50 text-left">
                <th className="px-4 py-2 font-medium text-gray-700 border-b">School ID</th>
                <th className="px-4 py-2 font-medium text-gray-700 border-b">Label</th>
                <th className="px-4 py-2 font-medium text-gray-700 border-b">Scope</th>
                <th className="px-4 py-2 font-medium text-gray-700 border-b">Status</th>
                <th className="px-4 py-2 font-medium text-gray-700 border-b">Size</th>
                <th className="px-4 py-2 font-medium text-gray-700 border-b">Date</th>
                <th className="px-4 py-2 font-medium text-gray-700 border-b">Actions</th>
              </tr>
            </thead>
            <tbody>
              {backups.map((b) => (
                <tr key={b.id} className="border-b hover:bg-gray-50">
                  <td className="px-4 py-2 font-mono text-xs text-gray-600">
                    <Link
                      href={`/admin/backups/${b.school_id}`}
                      className="hover:underline text-indigo-600"
                    >
                      {b.school_id.slice(0, 8)}…
                    </Link>
                  </td>
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
                    {fmtBytes(b.total_bytes)}
                  </td>
                  <td className="px-4 py-2 text-xs text-gray-600">
                    {fmtDate(b.created_at)}
                  </td>
                  <td className="px-4 py-2">
                    <Link
                      href={`/admin/backups/${b.school_id}`}
                      className="text-indigo-600 hover:underline text-xs"
                    >
                      View school
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex justify-center gap-2 mt-4">
          <button
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
            className="px-3 py-1 border rounded text-sm disabled:opacity-40"
          >
            Prev
          </button>
          <span className="px-3 py-1 text-sm text-gray-600">
            {page} / {totalPages}
          </span>
          <button
            disabled={page >= totalPages}
            onClick={() => setPage((p) => p + 1)}
            className="px-3 py-1 border rounded text-sm disabled:opacity-40"
          >
            Next
          </button>
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
                  School ID
                </label>
                <input
                  type="text"
                  value={modalSchoolId}
                  onChange={(e) => setModalSchoolId(e.target.value)}
                  placeholder="UUID"
                  className="w-full border rounded-md px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

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
                  placeholder="e.g. pre-migration backup"
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
