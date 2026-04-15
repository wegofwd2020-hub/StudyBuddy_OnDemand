"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import { useQuery, useQueryClient, useMutation } from "@tanstack/react-query";
import {
  Archive,
  ArchiveRestore,
  Layers,
  Plus,
  Search,
  Trash2,
} from "lucide-react";
import {
  archiveStream,
  deleteStream,
  listStreams,
  unarchiveStream,
  StreamResponse,
} from "@/lib/api/admin";
import { cn } from "@/lib/utils";

function relativeTime(iso: string): string {
  const s = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}

function canDelete(s: StreamResponse): boolean {
  return !s.is_system && s.is_archived && s.curricula_count === 0;
}

export default function AdminStreamsPage() {
  const qc = useQueryClient();
  const [filter, setFilter] = useState("");
  const [includeArchived, setIncludeArchived] = useState(false);

  const { data, isLoading, error } = useQuery({
    queryKey: ["admin-streams", includeArchived],
    queryFn: () => listStreams({ includeArchived }),
  });

  const filtered = useMemo(() => {
    if (!data) return [];
    const f = filter.trim().toLowerCase();
    const sorted = [...data].sort((a, b) => {
      if (a.is_system !== b.is_system) return a.is_system ? -1 : 1;
      return a.display_name.localeCompare(b.display_name);
    });
    if (!f) return sorted;
    return sorted.filter(
      (s) =>
        s.code.toLowerCase().includes(f) ||
        s.display_name.toLowerCase().includes(f),
    );
  }, [data, filter]);

  const archiveMut = useMutation({
    mutationFn: (code: string) => archiveStream(code),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-streams"] }),
  });
  const unarchiveMut = useMutation({
    mutationFn: (code: string) => unarchiveStream(code),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-streams"] }),
  });
  const deleteMut = useMutation({
    mutationFn: (code: string) => deleteStream(code),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-streams"] }),
  });

  return (
    <div className="mx-auto max-w-6xl p-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold text-gray-900">
            <Layers className="h-6 w-6 text-indigo-600" />
            Streams
          </h1>
          <p className="mt-0.5 text-sm text-gray-500">
            Curriculum partition for regional programmes (CBSE, IB, A-Levels, etc.)
          </p>
        </div>
        <Link
          href="/admin/streams/new"
          className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-indigo-500"
        >
          <Plus className="h-4 w-4" />
          New stream
        </Link>
      </div>

      <div className="mb-4 flex items-center gap-3">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute top-2.5 left-3 h-4 w-4 text-gray-400" />
          <input
            type="text"
            placeholder="Filter by code or display name"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="w-full rounded-lg border border-gray-300 bg-white py-2 pr-3 pl-9 text-sm focus:ring-2 focus:ring-indigo-500 focus:outline-none"
          />
        </div>
        <label className="inline-flex items-center gap-2 text-sm text-gray-700">
          <input
            type="checkbox"
            checked={includeArchived}
            onChange={(e) => setIncludeArchived(e.target.checked)}
            className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
          />
          Include archived
        </label>
      </div>

      {isLoading && <p className="text-sm text-gray-500">Loading…</p>}
      {error && (
        <p className="text-sm text-red-600">Failed to load streams.</p>
      )}

      {data && (
        <div className="overflow-hidden rounded-xl border border-gray-200 bg-white">
          <table className="w-full text-sm">
            <thead className="border-b border-gray-200 bg-gray-50 text-xs uppercase tracking-wide text-gray-500">
              <tr>
                <th className="px-4 py-3 text-left font-medium">Code</th>
                <th className="px-4 py-3 text-left font-medium">Display name</th>
                <th className="px-4 py-3 text-right font-medium">Curricula</th>
                <th className="px-4 py-3 text-left font-medium">Flags</th>
                <th className="px-4 py-3 text-left font-medium">Created</th>
                <th className="px-4 py-3 text-right font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filtered.map((s) => {
                const deletable = canDelete(s);
                return (
                  <tr key={s.code} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-mono text-xs text-gray-700">
                      <Link
                        href={`/admin/streams/${s.code}`}
                        className="hover:text-indigo-600 hover:underline"
                      >
                        {s.code}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-gray-900">{s.display_name}</td>
                    <td className="px-4 py-3 text-right font-mono text-xs text-gray-600">
                      {s.curricula_count}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex gap-1.5">
                        {s.is_system && (
                          <span className="rounded-md bg-green-50 px-2 py-0.5 text-xs font-medium text-green-700">
                            System
                          </span>
                        )}
                        {s.is_archived && (
                          <span className="rounded-md bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600">
                            Archived
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-500">
                      {relativeTime(s.created_at)}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="inline-flex items-center gap-1.5">
                        <Link
                          href={`/admin/streams/${s.code}`}
                          className="rounded-md px-2 py-1 text-xs text-indigo-600 hover:bg-indigo-50"
                        >
                          Edit
                        </Link>
                        {s.is_archived ? (
                          <button
                            onClick={() => unarchiveMut.mutate(s.code)}
                            disabled={unarchiveMut.isPending}
                            className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs text-gray-600 hover:bg-gray-100 disabled:opacity-50"
                            title="Unarchive"
                          >
                            <ArchiveRestore className="h-3.5 w-3.5" />
                          </button>
                        ) : (
                          <button
                            onClick={() => archiveMut.mutate(s.code)}
                            disabled={archiveMut.isPending}
                            className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs text-gray-600 hover:bg-gray-100 disabled:opacity-50"
                            title="Archive"
                          >
                            <Archive className="h-3.5 w-3.5" />
                          </button>
                        )}
                        <button
                          onClick={() => {
                            if (confirm(`Delete stream '${s.code}'? This cannot be undone.`)) {
                              deleteMut.mutate(s.code);
                            }
                          }}
                          disabled={!deletable || deleteMut.isPending}
                          title={
                            deletable
                              ? "Delete"
                              : s.is_system
                              ? "System streams can't be deleted"
                              : s.curricula_count > 0
                              ? `${s.curricula_count} curriculum(s) still use this stream — merge first`
                              : "Archive before deleting"
                          }
                          className={cn(
                            "inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs",
                            deletable
                              ? "text-red-600 hover:bg-red-50"
                              : "cursor-not-allowed text-gray-300",
                          )}
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-10 text-center text-sm text-gray-500">
                    No streams match.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
