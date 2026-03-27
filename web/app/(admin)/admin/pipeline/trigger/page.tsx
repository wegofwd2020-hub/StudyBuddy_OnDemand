"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAdmin, hasPermission } from "@/lib/hooks/useAdmin";
import { triggerAdminPipeline } from "@/lib/api/admin";
import { AlertCircle, ShieldOff } from "lucide-react";

export default function AdminPipelineTriggerPage() {
  const router = useRouter();
  const admin = useAdmin();

  const [grade, setGrade] = useState<number>(8);
  const [lang, setLang] = useState("en,fr");
  const [force, setForce] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (admin && !hasPermission(admin.role, "product_admin")) {
    return (
      <div className="p-8 max-w-lg mx-auto">
        <div className="flex items-center gap-3 text-red-600 mb-2">
          <ShieldOff className="h-5 w-5" />
          <span className="font-semibold">Access denied</span>
        </div>
        <p className="text-sm text-gray-500">
          Triggering pipeline jobs requires <strong>product_admin</strong> or higher.
        </p>
      </div>
    );
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const { job_id } = await triggerAdminPipeline(grade, lang, force);
      router.push(`/admin/pipeline/${job_id}`);
    } catch {
      setError("Failed to trigger pipeline job. Check that the grade and language are valid.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="p-8 max-w-lg mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-1">Trigger Pipeline Job</h1>
      <p className="text-sm text-gray-500 mb-8">
        Generate or regenerate content for a grade. The job runs asynchronously via Celery.
      </p>

      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">
              Grade
            </label>
            <select
              value={grade}
              onChange={(e) => setGrade(Number(e.target.value))}
              className="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              {[5, 6, 7, 8, 9, 10, 11, 12].map((g) => (
                <option key={g} value={g}>
                  Grade {g}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">
              Languages (comma-separated)
            </label>
            <input
              type="text"
              value={lang}
              onChange={(e) => setLang(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-indigo-500 font-mono"
              placeholder="en,fr,es"
            />
            <p className="text-xs text-gray-400 mt-1">
              Supported: <code>en</code>, <code>fr</code>, <code>es</code>
            </p>
          </div>

          <div className="flex items-center gap-3">
            <input
              id="force"
              type="checkbox"
              checked={force}
              onChange={(e) => setForce(e.target.checked)}
              className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
            />
            <label htmlFor="force" className="text-sm text-gray-700">
              Force regenerate (overrides existing content)
            </label>
          </div>

          {error && (
            <div className="flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
              <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <div className="flex gap-3 pt-2">
            <button
              type="submit"
              disabled={loading}
              className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors"
            >
              {loading ? "Triggering…" : "Trigger Job"}
            </button>
            <button
              type="button"
              onClick={() => router.back()}
              className="px-5 py-2.5 text-sm text-gray-600 hover:text-gray-900 transition-colors"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
