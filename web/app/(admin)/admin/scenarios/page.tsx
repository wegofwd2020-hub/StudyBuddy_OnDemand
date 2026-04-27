"use client";

import Link from "next/link";
import { Plus, Play, FileText } from "lucide-react";
import { useAdmin, hasPermission } from "@/lib/hooks/useAdmin";

// Static scenario index — replace with API call when backend persists scenarios
import contractLaw001 from "@/data/scenarios/contract_law_001_en.json";

const SCENARIOS = [contractLaw001] as const;

const DIFF_COLORS: Record<string, string> = {
  beginner:     "bg-green-100 text-green-700",
  intermediate: "bg-amber-100 text-amber-700",
  advanced:     "bg-red-100 text-red-700",
};

export default function ScenariosPage() {
  const admin = useAdmin();

  if (!admin) return null;
  if (!hasPermission(admin.role, "product_admin")) {
    return (
      <div className="p-8 text-center text-sm text-gray-500">
        You do not have permission to manage scenarios.
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl p-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Scenarios</h1>
          <p className="mt-1 text-sm text-gray-500">
            Scenario-based compliance training content.
          </p>
        </div>
        <Link
          href="/admin/scenarios/new"
          className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400"
        >
          <Plus className="h-4 w-4" />
          New Scenario
        </Link>
      </div>

      <div className="rounded-xl border bg-white shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">Title</th>
              <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">Domain</th>
              <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">Lang</th>
              <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">Difficulty</th>
              <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">Turns</th>
              <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">Video</th>
              <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {SCENARIOS.map((s) => {
              const hasVideo = Array.isArray((s as any).video_clips) && (s as any).video_clips.length > 0;
              const difficulty = (s as any).difficulty ?? "intermediate";
              return (
                <tr key={s.scenario_id} className="hover:bg-gray-50">
                  <td className="px-5 py-4 font-medium text-gray-900">{s.title}</td>
                  <td className="px-5 py-4 text-gray-500">{s.domain.replace(/_/g, " ")}</td>
                  <td className="px-5 py-4 text-gray-500 uppercase">{s.language}</td>
                  <td className="px-5 py-4">
                    <span className={`rounded-full px-2 py-0.5 text-xs font-semibold capitalize ${DIFF_COLORS[difficulty] ?? "bg-gray-100 text-gray-700"}`}>
                      {difficulty}
                    </span>
                  </td>
                  <td className="px-5 py-4 text-gray-500">{s.dialog.length}</td>
                  <td className="px-5 py-4">
                    {hasVideo
                      ? <span className="rounded-full bg-green-100 text-green-700 px-2 py-0.5 text-xs font-semibold">Ready</span>
                      : <span className="rounded-full bg-gray-100 text-gray-500 px-2 py-0.5 text-xs font-semibold">Text only</span>
                    }
                  </td>
                  <td className="px-5 py-4">
                    <div className="flex items-center gap-3">
                      <Link href="/jt" target="_blank" title="Preview"
                        className="flex items-center gap-1 text-xs text-indigo-600 hover:text-indigo-800 font-semibold">
                        <Play className="h-3.5 w-3.5" /> Preview
                      </Link>
                      <button title="View JSON" className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700 font-semibold">
                        <FileText className="h-3.5 w-3.5" /> JSON
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <p className="mt-4 text-xs text-gray-400">
        Scenarios are stored as JSON files in <code className="bg-gray-100 rounded px-1">web/data/scenarios/</code>.
        Backend persistence coming in a future sprint.
      </p>
    </div>
  );
}
