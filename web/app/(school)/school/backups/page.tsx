"use client";

import { useQuery } from "@tanstack/react-query";
import { useTeacher } from "@/lib/hooks/useTeacher";
import { schoolListBackups, type Backup } from "@/lib/api/backup";
import { Skeleton } from "@/components/ui/skeleton";
import { LinkButton } from "@/components/ui/link-button";
import { Database, RotateCcw } from "lucide-react";

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtBytes(bytes: number): string {
  if (bytes === 0) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

function scopeLabel(b: Backup): string {
  if (b.scope_type === "full") return "Full backup";
  if (b.scope_type === "grade") return `Grade ${b.scope_value}`;
  return b.scope_value ?? b.scope_type;
}

const STATUS_STYLE: Record<string, string> = {
  pending: "bg-yellow-50 text-yellow-700 border-yellow-200",
  running: "bg-blue-50 text-blue-700 border-blue-200",
  completed: "bg-green-50 text-green-700 border-green-200",
  failed: "bg-red-50 text-red-700 border-red-200",
};

function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium capitalize ${STATUS_STYLE[status] ?? "border-gray-200 bg-gray-50 text-gray-600"}`}
    >
      {status}
    </span>
  );
}

// ── Page ───────────────────────────────────────────────────────────────────────

export default function BackupsPage() {
  const teacher = useTeacher();
  const schoolId = teacher?.school_id ?? "";

  const { data, isLoading } = useQuery({
    queryKey: ["school-backups", schoolId],
    queryFn: () => schoolListBackups(schoolId),
    enabled: !!schoolId,
    staleTime: 30_000,
    refetchInterval: (query) => {
      const backups: Backup[] = query.state.data?.backups ?? [];
      return backups.some((b) => b.status === "pending" || b.status === "running")
        ? 5_000
        : false;
    },
  });

  const backups: Backup[] = data?.backups ?? [];

  return (
    <div className="max-w-4xl space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Database className="h-6 w-6 text-indigo-600" />
          <h1 className="text-2xl font-bold text-gray-900">Backup History</h1>
        </div>
        <LinkButton href="/school/restore-requests" size="sm">
          <RotateCcw className="mr-1.5 h-4 w-4" />
          Restore requests
        </LinkButton>
      </div>

      <p className="text-sm text-gray-500">
        Read-only view of your school&apos;s curriculum backups. Backups are created
        automatically on the configured schedule and can also be triggered by your
        platform administrator. To recover content from a backup, submit a restore
        request.
      </p>

      {/* Table */}
      {isLoading ? (
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-12 rounded-lg" />
          ))}
        </div>
      ) : backups.length === 0 ? (
        <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed border-gray-200 py-12 text-center">
          <Database className="h-8 w-8 text-gray-300" />
          <p className="text-sm font-medium text-gray-500">No backups yet</p>
          <p className="max-w-xs text-xs text-gray-400">
            Backups are created automatically overnight. Contact your administrator if you
            need an immediate backup.
          </p>
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg border border-gray-200">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-semibold text-gray-700">
                  Created
                </th>
                <th className="px-4 py-3 text-left font-semibold text-gray-700">
                  Label / Scope
                </th>
                <th className="px-4 py-3 text-left font-semibold text-gray-700">
                  Status
                </th>
                <th className="px-4 py-3 text-right font-semibold text-gray-700">
                  Files
                </th>
                <th className="px-4 py-3 text-right font-semibold text-gray-700">Size</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {backups.map((b) => (
                <tr key={b.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-gray-600 tabular-nums">
                    {new Date(b.created_at).toLocaleDateString()}{" "}
                    <span className="text-xs text-gray-400">
                      {new Date(b.created_at).toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-900">
                    {b.label || scopeLabel(b)}
                    {b.label && (
                      <span className="ml-2 text-xs text-gray-400">{scopeLabel(b)}</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={b.status} />
                  </td>
                  <td className="px-4 py-3 text-right text-gray-600 tabular-nums">
                    {b.file_count > 0 ? b.file_count : "—"}
                  </td>
                  <td className="px-4 py-3 text-right text-gray-600 tabular-nums">
                    {fmtBytes(b.total_bytes)}
                  </td>
                  <td className="px-4 py-3 text-right">
                    {b.status === "completed" && (
                      <LinkButton
                        href={`/school/restore-requests/new?backup_id=${b.id}`}
                        variant="outline"
                        size="sm"
                      >
                        Restore
                      </LinkButton>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="text-xs text-gray-400">
        Your plan retains the last 10 backups. Older backups are pruned automatically.
      </p>
    </div>
  );
}
