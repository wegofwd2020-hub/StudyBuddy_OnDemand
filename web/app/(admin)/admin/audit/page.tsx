"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getAuditLog } from "@/lib/api/admin";
import { useAdmin, hasPermission } from "@/lib/hooks/useAdmin";
import { ShieldOff, FileText } from "lucide-react";

export default function AdminAuditPage() {
  const admin = useAdmin();
  const [page, setPage] = useState(1);
  const [actionFilter, setActionFilter] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["admin", "audit", page, actionFilter],
    queryFn: () => getAuditLog(page, 50, actionFilter || undefined),
    staleTime: 30_000,
  });

  if (admin && !hasPermission(admin.role, "product_admin")) {
    return (
      <div className="mx-auto max-w-lg p-8">
        <div className="mb-2 flex items-center gap-3 text-red-600">
          <ShieldOff className="h-5 w-5" />
          <span className="font-semibold">Access denied</span>
        </div>
        <p className="text-sm text-gray-500">
          Viewing the audit log requires <strong>product_admin</strong> or higher.
        </p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl p-8">
      <h1 className="mb-1 text-2xl font-bold text-gray-900">Audit Log</h1>
      <p className="mb-6 text-sm text-gray-500">
        All admin actions recorded with actor and resource.
      </p>

      {/* Action filter */}
      <div className="mb-6 flex gap-3">
        <input
          type="text"
          value={actionFilter}
          onChange={(e) => {
            setActionFilter(e.target.value);
            setPage(1);
          }}
          placeholder="Filter by action (e.g. publish, block)…"
          className="w-64 rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
        />
      </div>

      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="h-12 animate-pulse rounded-lg bg-gray-100" />
          ))}
        </div>
      ) : data && data.entries.length > 0 ? (
        <>
          <p className="mb-3 text-xs text-gray-400">
            {data.total.toLocaleString()} entries
          </p>
          <div className="overflow-hidden rounded-xl border border-gray-200 bg-white">
            <table className="w-full text-sm">
              <thead className="border-b border-gray-200 bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Time</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Actor</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">
                    Action
                  </th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">
                    Resource
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {data.entries.map((entry) => (
                  <tr key={entry.audit_id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-xs whitespace-nowrap text-gray-500">
                      {new Date(entry.created_at).toLocaleString()}
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-xs text-gray-700">
                        {entry.actor_id.slice(0, 8)}…
                      </span>
                      <span className="ml-1.5 text-xs text-gray-400">
                        {entry.actor_role}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="rounded bg-indigo-50 px-1.5 py-0.5 font-mono text-xs text-indigo-700">
                        {entry.action}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-600">
                      <span className="text-gray-400">{entry.resource_type}/</span>
                      {entry.resource_id.slice(0, 12)}…
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-4 flex items-center gap-3">
            <button
              disabled={page === 1}
              onClick={() => setPage(page - 1)}
              className="rounded-lg bg-gray-100 px-3 py-1.5 text-sm text-gray-600 transition-colors hover:bg-gray-200 disabled:opacity-40"
            >
              Previous
            </button>
            <span className="text-sm text-gray-500">Page {page}</span>
            <button
              disabled={data.entries.length < 50}
              onClick={() => setPage(page + 1)}
              className="rounded-lg bg-gray-100 px-3 py-1.5 text-sm text-gray-600 transition-colors hover:bg-gray-200 disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </>
      ) : (
        <div className="py-16 text-center text-gray-400">
          <FileText className="mx-auto mb-3 h-10 w-10 opacity-40" />
          <p className="text-sm font-medium text-gray-600">
            {actionFilter ? `No entries matching "${actionFilter}".` : "No audit events recorded yet."}
          </p>
          {!actionFilter && (
            <p className="mt-1 text-xs text-gray-400">
              Events are recorded automatically when admins approve, publish, block, or annotate content.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
