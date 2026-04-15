"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useQueryClient, useMutation } from "@tanstack/react-query";
import {
  AlertCircle,
  Archive,
  ArchiveRestore,
  ArrowLeft,
  GitMerge,
  Trash2,
} from "lucide-react";
import {
  archiveStream,
  deleteStream,
  getStream,
  listStreams,
  mergeStream,
  unarchiveStream,
  updateStream,
} from "@/lib/api/admin";

function extractDetail(err: unknown): string | null {
  if (!err || typeof err !== "object" || !("response" in err)) return null;
  const resp = (err as { response?: { data?: { detail?: unknown } } }).response;
  const d = resp?.data?.detail;
  return typeof d === "string" ? d : null;
}

export default function AdminStreamDetailPage() {
  const params = useParams<{ code: string }>();
  const code = params.code;
  const router = useRouter();
  const qc = useQueryClient();

  const { data, isLoading, error } = useQuery({
    queryKey: ["admin-stream", code],
    queryFn: () => getStream(code),
  });

  const [editDisplay, setEditDisplay] = useState<string | null>(null);
  const [editDesc, setEditDesc] = useState<string | null>(null);
  const [mergeOpen, setMergeOpen] = useState(false);
  const [mergeTarget, setMergeTarget] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);

  const displayValue = editDisplay ?? data?.stream.display_name ?? "";
  const descValue = editDesc ?? data?.stream.description ?? "";
  const dirty =
    data !== undefined &&
    (displayValue !== data.stream.display_name ||
      (descValue || "") !== (data.stream.description || ""));

  const updateMut = useMutation({
    mutationFn: () =>
      updateStream(code, {
        display_name: displayValue,
        description: descValue || undefined,
      }),
    onSuccess: () => {
      setEditDisplay(null);
      setEditDesc(null);
      qc.invalidateQueries({ queryKey: ["admin-stream", code] });
      qc.invalidateQueries({ queryKey: ["admin-streams"] });
    },
    onError: (err: unknown) => {
      setActionError(extractDetail(err) ?? "Update failed.");
    },
  });

  const archiveMut = useMutation({
    mutationFn: () => archiveStream(code),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-stream", code] }),
  });
  const unarchiveMut = useMutation({
    mutationFn: () => unarchiveStream(code),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-stream", code] }),
  });

  const mergeMut = useMutation({
    mutationFn: () => mergeStream(code, mergeTarget),
    onSuccess: () => {
      setMergeOpen(false);
      qc.invalidateQueries();
      router.push(`/admin/streams/${mergeTarget}`);
    },
    onError: (err: unknown) => {
      setActionError(extractDetail(err) ?? "Merge failed.");
    },
  });

  const deleteMut = useMutation({
    mutationFn: () => deleteStream(code),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-streams"] });
      router.push("/admin/streams");
    },
    onError: (err: unknown) => {
      setActionError(extractDetail(err) ?? "Delete failed.");
    },
  });

  const targetsQuery = useQuery({
    queryKey: ["admin-streams", "merge-targets"],
    queryFn: () => listStreams({ includeArchived: false }),
    enabled: mergeOpen,
  });
  const targetOptions = useMemo(
    () =>
      (targetsQuery.data ?? [])
        .filter((s) => s.code !== code)
        .sort((a, b) => a.display_name.localeCompare(b.display_name)),
    [targetsQuery.data, code],
  );

  if (isLoading) return <p className="p-8 text-sm text-gray-500">Loading…</p>;
  if (error || !data)
    return (
      <div className="p-8">
        <p className="text-sm text-red-600">Stream not found.</p>
        <Link href="/admin/streams" className="mt-2 inline-block text-sm text-indigo-600">
          Back to Streams
        </Link>
      </div>
    );

  const { stream, curricula } = data;
  const deletable =
    !stream.is_system && stream.is_archived && stream.curricula_count === 0;

  return (
    <div className="mx-auto max-w-4xl p-8">
      <Link
        href="/admin/streams"
        className="mb-4 inline-flex items-center gap-1.5 text-sm text-gray-500 transition-colors hover:text-gray-900"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Streams
      </Link>

      <div className="mb-6 flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-gray-900">{stream.display_name}</h1>
            {stream.is_system && (
              <span className="rounded-md bg-green-50 px-2 py-0.5 text-xs font-medium text-green-700">
                System
              </span>
            )}
            {stream.is_archived && (
              <span className="rounded-md bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600">
                Archived
              </span>
            )}
          </div>
          <p className="mt-0.5 font-mono text-sm text-gray-500">{stream.code}</p>
        </div>
        <div className="flex gap-2">
          {!stream.is_system && (
            <button
              onClick={() => {
                setActionError(null);
                setMergeOpen(true);
              }}
              className="inline-flex items-center gap-1.5 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 transition-colors hover:bg-gray-50"
            >
              <GitMerge className="h-4 w-4" />
              Merge into…
            </button>
          )}
          {stream.is_archived ? (
            <button
              onClick={() => unarchiveMut.mutate()}
              disabled={unarchiveMut.isPending}
              className="inline-flex items-center gap-1.5 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 transition-colors hover:bg-gray-50 disabled:opacity-50"
            >
              <ArchiveRestore className="h-4 w-4" />
              Unarchive
            </button>
          ) : (
            <button
              onClick={() => archiveMut.mutate()}
              disabled={archiveMut.isPending}
              className="inline-flex items-center gap-1.5 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 transition-colors hover:bg-gray-50 disabled:opacity-50"
            >
              <Archive className="h-4 w-4" />
              Archive
            </button>
          )}
          <button
            onClick={() => {
              if (confirm(`Delete stream '${stream.code}'?`)) deleteMut.mutate();
            }}
            disabled={!deletable || deleteMut.isPending}
            title={
              deletable
                ? "Delete"
                : stream.is_system
                ? "System streams can't be deleted"
                : stream.curricula_count > 0
                ? "Merge curricula away before deleting"
                : "Archive before deleting"
            }
            className={
              deletable
                ? "inline-flex items-center gap-1.5 rounded-lg border border-red-200 bg-white px-3 py-2 text-sm text-red-600 transition-colors hover:bg-red-50"
                : "inline-flex cursor-not-allowed items-center gap-1.5 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-300"
            }
          >
            <Trash2 className="h-4 w-4" />
            Delete
          </button>
        </div>
      </div>

      {actionError && (
        <div className="mb-4 flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{actionError}</span>
        </div>
      )}

      <section className="mb-6 rounded-xl border border-gray-200 bg-white p-6">
        <h2 className="mb-4 text-sm font-semibold text-gray-900">Edit</h2>
        <div className="space-y-4">
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-500">Code</label>
            <input
              type="text"
              value={stream.code}
              disabled
              className="w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 font-mono text-sm text-gray-500"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-500">Display name</label>
            <input
              type="text"
              value={displayValue}
              onChange={(e) => setEditDisplay(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-500">Description</label>
            <textarea
              value={descValue}
              onChange={(e) => setEditDesc(e.target.value)}
              rows={3}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
            />
          </div>
          <button
            onClick={() => {
              setActionError(null);
              updateMut.mutate();
            }}
            disabled={!dirty || updateMut.isPending}
            className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-indigo-500 disabled:opacity-50"
          >
            {updateMut.isPending ? "Saving…" : "Save changes"}
          </button>
        </div>
      </section>

      <section className="rounded-xl border border-gray-200 bg-white p-6">
        <h2 className="mb-4 text-sm font-semibold text-gray-900">
          Curricula using this stream ({stream.curricula_count})
        </h2>
        {curricula.length === 0 ? (
          <p className="text-sm text-gray-500">None yet.</p>
        ) : (
          <ul className="divide-y divide-gray-100">
            {curricula.map((c) => (
              <li key={c.curriculum_id} className="flex items-center justify-between py-2 text-sm">
                <div>
                  <p className="font-mono text-xs text-gray-500">{c.curriculum_id}</p>
                  <p className="text-gray-900">{c.name ?? `Grade ${c.grade}`}</p>
                </div>
                <span className="text-xs text-gray-500">
                  Grade {c.grade} · {c.year}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      {mergeOpen && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-lg">
            <h3 className="text-lg font-semibold text-gray-900">
              Merge {stream.display_name} into…
            </h3>
            <p className="mt-1 text-sm text-gray-600">
              This reassigns <strong>{stream.curricula_count}</strong> curriculum(s) to
              the target stream and archives <code>{stream.code}</code>. Cannot be undone
              automatically.
            </p>
            <select
              value={mergeTarget}
              onChange={(e) => setMergeTarget(e.target.value)}
              className="mt-4 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:outline-none"
            >
              <option value="">Select target stream…</option>
              {targetOptions.map((s) => (
                <option key={s.code} value={s.code}>
                  {s.display_name} ({s.code})
                </option>
              ))}
            </select>
            <div className="mt-5 flex justify-end gap-2">
              <button
                onClick={() => setMergeOpen(false)}
                className="rounded-lg px-4 py-2 text-sm text-gray-600 hover:bg-gray-100"
              >
                Cancel
              </button>
              <button
                onClick={() => mergeMut.mutate()}
                disabled={!mergeTarget || mergeMut.isPending}
                className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-indigo-500 disabled:opacity-50"
              >
                {mergeMut.isPending ? "Merging…" : "Merge"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
