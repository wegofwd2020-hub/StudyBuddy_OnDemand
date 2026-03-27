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

  if (admin && !hasPermission(admin.role, "product_admin")) {
    return (
      <div className="p-8 max-w-lg mx-auto">
        <div className="flex items-center gap-3 text-red-600 mb-2">
          <ShieldOff className="h-5 w-5" />
          <span className="font-semibold">Access denied</span>
        </div>
        <p className="text-sm text-gray-500">
          Viewing the audit log requires <strong>product_admin</strong> or higher.
        </p>
      </div>
    );
  }

  const { data, isLoading } = useQuery({
    queryKey: ["admin", "audit", page, actionFilter],
    queryFn: () => getAuditLog(page, 50, actionFilter || undefined),
    staleTime: 30_000,
  });

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-1">Audit Log</h1>
      <p className="text-sm text-gray-500 mb-6">All admin actions recorded with actor and resource.</p>

      {/* Action filter */}
      <div className="flex gap-3 mb-6">
        <input
          type="text"
          value={actionFilter}
          onChange={(e) => { setActionFilter(e.target.value); setPage(1); }}
          placeholder="Filter by action (e.g. publish, block)…"
          className="w-64 px-3 py-2 rounded-lg border border-gray-300 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
      </div>

      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="h-12 bg-gray-100 rounded-lg animate-pulse" />
          ))}
        </div>
      ) : data && data.entries.length > 0 ? (
        <>
          <p className="text-xs text-gray-400 mb-3">{data.total.toLocaleString()} entries</p>
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Time</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Actor</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Action</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Resource</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {data.entries.map((entry) => (
                  <tr key={entry.audit_id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-gray-500 text-xs whitespace-nowrap">
                      {new Date(entry.created_at).toLocaleString()}
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-gray-700 text-xs">{entry.actor_id.slice(0, 8)}…</span>
                      <span className="ml-1.5 text-gray-400 text-xs">{entry.actor_role}</span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="font-mono text-xs text-indigo-700 bg-indigo-50 px-1.5 py-0.5 rounded">
                        {entry.action}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-600 text-xs">
                      <span className="text-gray-400">{entry.resource_type}/</span>
                      {entry.resource_id.slice(0, 12)}…
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="flex items-center gap-3 mt-4">
            <button
              disabled={page === 1}
              onClick={() => setPage(page - 1)}
              className="px-3 py-1.5 text-sm text-gray-600 bg-gray-100 hover:bg-gray-200 disabled:opacity-40 rounded-lg transition-colors"
            >
              Previous
            </button>
            <span className="text-sm text-gray-500">Page {page}</span>
            <button
              disabled={data.entries.length < 50}
              onClick={() => setPage(page + 1)}
              className="px-3 py-1.5 text-sm text-gray-600 bg-gray-100 hover:bg-gray-200 disabled:opacity-40 rounded-lg transition-colors"
            >
              Next
            </button>
          </div>
        </>
      ) : (
        <div className="text-center py-16 text-gray-400">
          <FileText className="h-10 w-10 mx-auto mb-3 opacity-40" />
          <p className="text-sm">No audit entries found.</p>
        </div>
      )}
    </div>
  );
}
