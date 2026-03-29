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
      <div className="mx-auto max-w-lg p-8">
        <div className="mb-2 flex items-center gap-3 text-red-600">
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
      setError(
        "Failed to trigger pipeline job. Check that the grade and language are valid.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-lg p-8">
      <h1 className="mb-1 text-2xl font-bold text-gray-900">Trigger Pipeline Job</h1>
      <p className="mb-8 text-sm text-gray-500">
        Generate or regenerate content for a grade. The job runs asynchronously via
        Celery.
      </p>

      <div className="rounded-xl border border-gray-200 bg-white p-6">
        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="mb-1.5 block text-sm font-medium text-gray-700">
              Grade
            </label>
            <select
              value={grade}
              onChange={(e) => setGrade(Number(e.target.value))}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
            >
              {[5, 6, 7, 8, 9, 10, 11, 12].map((g) => (
                <option key={g} value={g}>
                  Grade {g}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1.5 block text-sm font-medium text-gray-700">
              Languages (comma-separated)
            </label>
            <input
              type="text"
              value={lang}
              onChange={(e) => setLang(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 font-mono text-sm text-gray-900 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
              placeholder="en,fr,es"
            />
            <p className="mt-1 text-xs text-gray-400">
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
            <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <div className="flex gap-3 pt-2">
            <button
              type="submit"
              disabled={loading}
              className="rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-indigo-500 disabled:opacity-50"
            >
              {loading ? "Triggering…" : "Trigger Job"}
            </button>
            <button
              type="button"
              onClick={() => router.back()}
              className="px-5 py-2.5 text-sm text-gray-600 transition-colors hover:text-gray-900"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
