"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { RefreshCw, Clock, Save } from "lucide-react";
import {
  BackupSchedule,
  listBackupSchedules,
  updateBackupSchedule,
} from "@/lib/api/backup";

function humanCron(cron: string | null): string {
  if (!cron) return "Not scheduled";
  const parts = cron.trim().split(/\s+/);
  if (parts.length !== 5) return cron;
  const [min, hour, dom, month, dow] = parts;

  if (dom === "*" && month === "*" && dow === "*") {
    const h = parseInt(hour, 10);
    const m = parseInt(min, 10);
    if (!isNaN(h) && !isNaN(m)) {
      const hh = String(h).padStart(2, "0");
      const mm = String(m).padStart(2, "0");
      return `Nightly at ${hh}:${mm} UTC`;
    }
  }
  if (dom === "*" && month === "*" && dow !== "*") {
    const days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
    const dayNum = parseInt(dow, 10);
    if (!isNaN(dayNum) && dayNum >= 0 && dayNum <= 6) {
      const h = parseInt(hour, 10);
      const m = parseInt(min, 10);
      if (!isNaN(h) && !isNaN(m)) {
        const hh = String(h).padStart(2, "0");
        const mm = String(m).padStart(2, "0");
        return `Weekly on ${days[dayNum]} at ${hh}:${mm} UTC`;
      }
    }
  }
  return cron;
}

export default function BackupSchedulesPage() {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [schedules, setSchedules] = useState<BackupSchedule[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Per-row edit state: schoolId → draft cron value
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState<Record<string, boolean>>({});
  const [saveErrors, setSaveErrors] = useState<Record<string, string>>({});
  const [saveSuccess, setSaveSuccess] = useState<Record<string, boolean>>({});

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
      const data: BackupSchedule[] = await listBackupSchedules();
      setSchedules(data);
      // Initialize drafts from current values
      const initial: Record<string, string> = {};
      for (const s of data) {
        initial[s.school_id] = s.cron ?? "";
      }
      setDrafts(initial);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load schedules");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleSave(schoolId: string) {
    setSaving((prev) => ({ ...prev, [schoolId]: true }));
    setSaveErrors((prev) => ({ ...prev, [schoolId]: "" }));
    setSaveSuccess((prev) => ({ ...prev, [schoolId]: false }));
    try {
      await updateBackupSchedule(schoolId, drafts[schoolId] ?? "");
      setSaveSuccess((prev) => ({ ...prev, [schoolId]: true }));
      setTimeout(() => {
        setSaveSuccess((prev) => ({ ...prev, [schoolId]: false }));
      }, 2000);
    } catch (e: unknown) {
      setSaveErrors((prev) => ({
        ...prev,
        [schoolId]: e instanceof Error ? e.message : "Save failed",
      }));
    } finally {
      setSaving((prev) => ({ ...prev, [schoolId]: false }));
    }
  }

  if (!token) return null;

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <Clock className="w-5 h-5 text-gray-600" />
          <h1 className="text-xl font-semibold text-gray-900">
            Backup Schedules
          </h1>
          <span className="text-sm text-gray-500 ml-2">
            ({schedules.length} schools)
          </span>
        </div>
        <button
          onClick={load}
          className="flex items-center gap-1 px-3 py-1.5 text-sm border border-gray-300 rounded-md hover:bg-gray-50"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md text-red-700 text-sm">
          {error}
        </div>
      )}

      <p className="text-sm text-gray-500 mb-4">
        Cron expressions are in standard 5-field format (minute hour day month weekday).
        Leave blank to disable scheduled backups for a school.
        The nightly coordinator runs at{" "}
        <span className="font-mono text-xs bg-gray-100 px-1 rounded">02:30 UTC</span>{" "}
        and triggers a full backup for every school with a non-empty schedule.
      </p>

      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading schedules…</div>
      ) : schedules.length === 0 ? (
        <div className="text-center py-12 text-gray-500">No schools found.</div>
      ) : (
        <div className="space-y-0 border border-gray-200 rounded-lg overflow-hidden">
          {schedules.map((s, idx) => (
            <div
              key={s.school_id}
              className={`flex items-center gap-3 px-4 py-3 ${
                idx % 2 === 0 ? "bg-white" : "bg-gray-50"
              }`}
            >
              {/* School ID */}
              <span className="font-mono text-xs text-gray-600 w-48 flex-shrink-0 truncate">
                {s.school_id}
              </span>

              {/* Cron input */}
              <div className="flex-1">
                <input
                  type="text"
                  value={drafts[s.school_id] ?? ""}
                  onChange={(e) =>
                    setDrafts((prev) => ({
                      ...prev,
                      [s.school_id]: e.target.value,
                    }))
                  }
                  placeholder="0 2 * * *"
                  className="w-full border border-gray-300 rounded-md px-3 py-1.5 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
                <p className="text-xs text-gray-400 mt-0.5">
                  {humanCron(drafts[s.school_id] || null)}
                </p>
                {saveErrors[s.school_id] && (
                  <p className="text-xs text-red-600 mt-0.5">
                    {saveErrors[s.school_id]}
                  </p>
                )}
              </div>

              {/* Save button */}
              <button
                onClick={() => handleSave(s.school_id)}
                disabled={saving[s.school_id]}
                className={`flex items-center gap-1 px-3 py-1.5 text-sm rounded-md flex-shrink-0 transition-colors ${
                  saveSuccess[s.school_id]
                    ? "bg-green-600 text-white"
                    : "bg-indigo-600 text-white hover:bg-indigo-700"
                } disabled:opacity-50`}
              >
                <Save className="w-3.5 h-3.5" />
                {saving[s.school_id]
                  ? "Saving…"
                  : saveSuccess[s.school_id]
                  ? "Saved"
                  : "Save"}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
