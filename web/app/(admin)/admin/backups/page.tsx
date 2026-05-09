"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { RefreshCw, Plus, Archive } from "lucide-react";
import { Backup, listAllBackups, createBackup } from "@/lib/api/backup";

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
      (b) => b.status === "running" || b.status === "pending",
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
    <div className="mx-auto max-w-6xl p-6">
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Archive className="h-5 w-5 text-gray-600" />
          <h1 className="text-xl font-semibold text-gray-900">Curriculum Backups</h1>
          <span className="ml-2 text-sm text-gray-500">({total} total)</span>
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

      {error && (
        <div className="mb-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {loading ? (
        <div className="py-12 text-center text-gray-500">Loading backups…</div>
      ) : backups.length === 0 ? (
        <div className="py-12 text-center text-gray-500">No backups found.</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="bg-gray-50 text-left">
                <th className="border-b px-4 py-2 font-medium text-gray-700">
                  School ID
                </th>
                <th className="border-b px-4 py-2 font-medium text-gray-700">Label</th>
                <th className="border-b px-4 py-2 font-medium text-gray-700">Scope</th>
                <th className="border-b px-4 py-2 font-medium text-gray-700">Status</th>
                <th className="border-b px-4 py-2 font-medium text-gray-700">Size</th>
                <th className="border-b px-4 py-2 font-medium text-gray-700">Date</th>
                <th className="border-b px-4 py-2 font-medium text-gray-700">Actions</th>
              </tr>
            </thead>
            <tbody>
              {backups.map((b) => (
                <tr key={b.id} className="border-b hover:bg-gray-50">
                  <td className="px-4 py-2 font-mono text-xs text-gray-600">
                    <Link
                      href={`/admin/backups/${b.school_id}`}
                      className="text-indigo-600 hover:underline"
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
                      className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
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
                      className="text-xs text-indigo-600 hover:underline"
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
        <div className="mt-4 flex justify-center gap-2">
          <button
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
            className="rounded border px-3 py-1 text-sm disabled:opacity-40"
          >
            Prev
          </button>
          <span className="px-3 py-1 text-sm text-gray-600">
            {page} / {totalPages}
          </span>
          <button
            disabled={page >= totalPages}
            onClick={() => setPage((p) => p + 1)}
            className="rounded border px-3 py-1 text-sm disabled:opacity-40"
          >
            Next
          </button>
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
                  School ID
                </label>
                <input
                  type="text"
                  value={modalSchoolId}
                  onChange={(e) => setModalSchoolId(e.target.value)}
                  placeholder="UUID"
                  className="w-full rounded-md border px-3 py-2 font-mono text-sm focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                />
              </div>

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
                  placeholder="e.g. pre-migration backup"
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
