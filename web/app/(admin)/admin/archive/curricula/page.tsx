"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArchiveX, ArchiveRestore, Filter, AlertTriangle } from "lucide-react";
import {
  listArchivedCurricula,
  unarchiveCurriculum,
  type ArchiveCurriculaFilters,
} from "@/lib/api/admin";
import { useAdmin } from "@/lib/hooks/useAdmin";

function ttlBadge(days: number | null) {
  if (days === null) return <span className="text-gray-400 text-xs">—</span>;
  const cls =
    days < 30
      ? "bg-red-100 text-red-700"
      : days < 90
        ? "bg-yellow-100 text-yellow-700"
        : "bg-green-100 text-green-700";
  return (
    <span className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${cls}`}>
      {days}d left
    </span>
  );
}

function fmtDate(iso: string | null) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export default function ArchivedCurriculaPage() {
  const qc = useQueryClient();
  const admin = useAdmin();
  const isSuperAdmin = admin?.role === "super_admin";

  const [filters, setFilters] = useState<ArchiveCurriculaFilters>({});
  const [search, setSearch] = useState("");
  const [unarchiving, setUnarchiving] = useState<string | null>(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ["admin-archive-curricula", filters],
    queryFn: () => listArchivedCurricula(filters),
  });

  const unarchiveMut = useMutation({
    mutationFn: (id: string) => unarchiveCurriculum(id),
    onMutate: (id) => setUnarchiving(id),
    onSettled: () => setUnarchiving(null),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-archive-curricula"] }),
  });

  const rows = (data ?? []).filter((r) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      r.curriculum_id.toLowerCase().includes(q) ||
      (r.name ?? "").toLowerCase().includes(q) ||
      (r.school_name ?? "").toLowerCase().includes(q)
    );
  });

  return (
    <div className="mx-auto max-w-7xl p-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold text-gray-900">
            <ArchiveX className="h-6 w-6 text-red-600" />
            Archived Curricula
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            Platform-wide view of archived curricula. Rows are hard-deleted 1 year after archive.
          </p>
        </div>
        <span className="rounded bg-gray-100 px-3 py-1 text-sm font-medium text-gray-600">
          {rows.length} record{rows.length !== 1 ? "s" : ""}
        </span>
      </div>

      {/* Filters */}
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-1 text-sm text-gray-500">
          <Filter className="h-4 w-4" />
          Filters:
        </div>

        <input
          type="text"
          placeholder="Search name / ID / school…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="rounded border border-gray-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />

        <select
          value={filters.owner_type ?? ""}
          onChange={(e) =>
            setFilters((f) => ({
              ...f,
              owner_type: e.target.value ? (e.target.value as "platform" | "school") : undefined,
            }))
          }
          className="rounded border border-gray-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          <option value="">All owners</option>
          <option value="platform">Platform</option>
          <option value="school">School</option>
        </select>

        <select
          value={filters.grade ?? ""}
          onChange={(e) =>
            setFilters((f) => ({
              ...f,
              grade: e.target.value ? Number(e.target.value) : undefined,
            }))
          }
          className="rounded border border-gray-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          <option value="">All grades</option>
          {[5, 6, 7, 8, 9, 10, 11, 12].map((g) => (
            <option key={g} value={g}>
              Grade {g}
            </option>
          ))}
        </select>

        <select
          value={filters.days_until_ttl_max ?? ""}
          onChange={(e) =>
            setFilters((f) => ({
              ...f,
              days_until_ttl_max: e.target.value ? Number(e.target.value) : undefined,
            }))
          }
          className="rounded border border-gray-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          <option value="">Any TTL</option>
          <option value="30">Expiring &lt; 30 days</option>
          <option value="90">Expiring &lt; 90 days</option>
          <option value="180">Expiring &lt; 180 days</option>
        </select>

        {(filters.owner_type || filters.grade || filters.days_until_ttl_max || search) && (
          <button
            onClick={() => {
              setFilters({});
              setSearch("");
            }}
            className="text-sm text-indigo-600 underline"
          >
            Clear
          </button>
        )}
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="py-16 text-center text-sm text-gray-400">Loading…</div>
      ) : error ? (
        <div className="flex items-center gap-2 rounded border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          <AlertTriangle className="h-4 w-4" />
          Failed to load archived curricula.
        </div>
      ) : rows.length === 0 ? (
        <div className="py-16 text-center text-sm text-gray-400">
          No archived curricula match the current filters.
        </div>
      ) : (
        <div className="overflow-x-auto rounded border border-gray-200">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                {[
                  "Curriculum",
                  "Owner",
                  "Grade",
                  "Year",
                  "Archived",
                  "Reason",
                  "TTL",
                  ...(isSuperAdmin ? ["Action"] : []),
                ].map((h) => (
                  <th
                    key={h}
                    className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {rows.map((r) => (
                <tr key={r.curriculum_id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <div className="font-medium text-gray-900">{r.name ?? "—"}</div>
                    <div className="font-mono text-xs text-gray-400">{r.curriculum_id}</div>
                  </td>
                  <td className="px-4 py-3">
                    {r.owner_type === "platform" ? (
                      <span className="rounded bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-700">
                        Platform
                      </span>
                    ) : (
                      <span className="text-gray-700">{r.school_name ?? r.school_id ?? "—"}</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-700">
                    {r.grade != null ? `Grade ${r.grade}` : "—"}
                  </td>
                  <td className="px-4 py-3 text-gray-700">{r.year ?? "—"}</td>
                  <td className="px-4 py-3">
                    <div className="text-gray-700">{fmtDate(r.archived_at)}</div>
                    {r.archive_event_type === "curriculum.archive_by_platform_admin" && (
                      <div className="mt-0.5 text-xs text-orange-600">by platform admin</div>
                    )}
                  </td>
                  <td className="max-w-xs px-4 py-3 text-gray-500">
                    {r.archive_reason ? (
                      <span title={r.archive_reason} className="line-clamp-2">
                        {r.archive_reason}
                      </span>
                    ) : (
                      <span className="text-gray-300">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3">{ttlBadge(r.days_until_ttl)}</td>
                  {isSuperAdmin && (
                    <td className="px-4 py-3">
                      <button
                        onClick={() => unarchiveMut.mutate(r.curriculum_id)}
                        disabled={unarchiving === r.curriculum_id}
                        className="flex items-center gap-1 rounded border border-gray-300 px-2 py-1 text-xs text-gray-600 hover:border-indigo-400 hover:text-indigo-600 disabled:opacity-40"
                      >
                        <ArchiveRestore className="h-3.5 w-3.5" />
                        {unarchiving === r.curriculum_id ? "…" : "Unarchive"}
                      </button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
