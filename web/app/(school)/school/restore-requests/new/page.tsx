"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useTeacher } from "@/lib/hooks/useTeacher";
import {
  schoolListBackups,
  schoolSubmitRestoreRequest,
  type Backup,
} from "@/lib/api/backup";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { RotateCcw, Database, ChevronRight, ChevronLeft } from "lucide-react";

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtBytes(bytes: number): string {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

function scopeLabel(b: Backup): string {
  if (b.scope_type === "full") return "Full backup";
  if (b.scope_type === "grade") return `Grade ${b.scope_value}`;
  return b.scope_value ?? b.scope_type;
}

// ── Step 1 — Pick a backup ────────────────────────────────────────────────────

function StepPickBackup({
  backups,
  selected,
  onSelect,
  onNext,
}: {
  backups: Backup[];
  selected: string;
  onSelect: (id: string) => void;
  onNext: () => void;
}) {
  const completed = backups.filter((b) => b.status === "completed");

  return (
    <div className="space-y-4">
      <h2 className="text-base font-semibold text-gray-800">Step 1 of 3 — Select a backup</h2>
      <p className="text-sm text-gray-500">
        Choose the backup to restore from. Only completed backups are available.
      </p>

      {completed.length === 0 ? (
        <div className="rounded-lg border border-dashed border-gray-200 p-8 text-center text-sm text-gray-400">
          No completed backups available. Contact your administrator.
        </div>
      ) : (
        <div className="space-y-2">
          {completed.map((b) => (
            <label
              key={b.id}
              className={`flex cursor-pointer items-start gap-3 rounded-lg border p-3 transition-colors ${
                selected === b.id
                  ? "border-indigo-400 bg-indigo-50"
                  : "border-gray-200 hover:bg-gray-50"
              }`}
            >
              <input
                type="radio"
                name="backup"
                value={b.id}
                checked={selected === b.id}
                onChange={() => onSelect(b.id)}
                className="mt-0.5"
              />
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-medium text-gray-900">
                    {b.label || scopeLabel(b)}
                  </span>
                  <span className="text-xs text-gray-400 tabular-nums">
                    {new Date(b.created_at).toLocaleDateString()}{" "}
                    {new Date(b.created_at).toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </span>
                </div>
                <p className="mt-0.5 text-xs text-gray-500">
                  {scopeLabel(b)} · {b.file_count} files · {fmtBytes(b.total_bytes)}
                </p>
              </div>
            </label>
          ))}
        </div>
      )}

      <div className="flex justify-end">
        <Button onClick={onNext} disabled={!selected}>
          Next <ChevronRight className="ml-1 h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}

// ── Step 2 — Configure scope ──────────────────────────────────────────────────

function StepConfigureScope({
  backup,
  scopeType,
  scopeValue,
  onScopeType: setScopeType,
  onScopeValue: setScopeValue,
  sideBySide,
  onSideBySide: setSideBySide,
  onBack,
  onNext,
}: {
  backup: Backup;
  scopeType: string;
  scopeValue: string;
  onScopeType: (v: string) => void;
  onScopeValue: (v: string) => void;
  sideBySide: boolean;
  onSideBySide: (v: boolean) => void;
  onBack: () => void;
  onNext: () => void;
}) {
  const canNarrow = backup.scope_type === "full";

  return (
    <div className="space-y-5">
      <h2 className="text-base font-semibold text-gray-800">Step 2 of 3 — Restore scope</h2>

      <div className="rounded-lg border border-gray-100 bg-gray-50 p-3 text-sm text-gray-600">
        Restoring from: <span className="font-medium text-gray-900">{backup.label || scopeLabel(backup)}</span>
        {" · "}{new Date(backup.created_at).toLocaleDateString()}
      </div>

      <div className="space-y-2">
        <label className="block text-sm font-medium text-gray-700">What to restore</label>
        <div className="space-y-2">
          <label className="flex cursor-pointer items-start gap-3 rounded-lg border border-gray-200 p-3 hover:bg-gray-50">
            <input
              type="radio"
              name="scope_type"
              value="full"
              checked={scopeType === "full"}
              onChange={() => { setScopeType("full"); setScopeValue(""); }}
              className="mt-0.5"
            />
            <div>
              <p className="font-medium text-gray-900 text-sm">Full restore</p>
              <p className="text-xs text-gray-500">Restore all curricula from this backup</p>
            </div>
          </label>

          {canNarrow && (
            <>
              <label className="flex cursor-pointer items-start gap-3 rounded-lg border border-gray-200 p-3 hover:bg-gray-50">
                <input
                  type="radio"
                  name="scope_type"
                  value="grade"
                  checked={scopeType === "grade"}
                  onChange={() => setScopeType("grade")}
                  className="mt-0.5"
                />
                <div className="flex-1">
                  <p className="font-medium text-gray-900 text-sm">Grade only</p>
                  <p className="text-xs text-gray-500">Restore curricula for a specific grade</p>
                  {scopeType === "grade" && (
                    <input
                      type="number"
                      min={5}
                      max={12}
                      placeholder="Grade (5–12)"
                      value={scopeValue}
                      onChange={(e) => setScopeValue(e.target.value)}
                      className="mt-2 w-32 rounded-md border border-gray-300 px-2 py-1 text-sm"
                    />
                  )}
                </div>
              </label>

              <label className="flex cursor-pointer items-start gap-3 rounded-lg border border-gray-200 p-3 hover:bg-gray-50">
                <input
                  type="radio"
                  name="scope_type"
                  value="name"
                  checked={scopeType === "name"}
                  onChange={() => setScopeType("name")}
                  className="mt-0.5"
                />
                <div className="flex-1">
                  <p className="font-medium text-gray-900 text-sm">Curriculum name</p>
                  <p className="text-xs text-gray-500">Restore a specific curriculum by name</p>
                  {scopeType === "name" && (
                    <input
                      type="text"
                      placeholder="e.g. Grade 8 Science"
                      value={scopeValue}
                      onChange={(e) => setScopeValue(e.target.value)}
                      className="mt-2 w-full rounded-md border border-gray-300 px-2 py-1 text-sm"
                    />
                  )}
                </div>
              </label>
            </>
          )}
        </div>
      </div>

      {/* Side-by-side option */}
      <div className="space-y-1">
        <label className="flex cursor-pointer items-start gap-3 rounded-lg border border-gray-200 p-3 hover:bg-gray-50">
          <input
            type="checkbox"
            checked={sideBySide}
            onChange={(e) => setSideBySide(e.target.checked)}
            className="mt-0.5"
          />
          <div>
            <p className="font-medium text-gray-900 text-sm">Side-by-side restore</p>
            <p className="text-xs text-gray-500">
              Restore to a new versioned catalog (<code className="text-xs">{"{name}.{yyyymmdd}"}</code>)
              without touching the live curriculum. Recommended if you&apos;re unsure.
            </p>
          </div>
        </label>
      </div>

      <div className="flex items-center justify-between">
        <Button variant="outline" onClick={onBack}>
          <ChevronLeft className="mr-1 h-4 w-4" /> Back
        </Button>
        <Button
          onClick={onNext}
          disabled={
            (scopeType === "grade" && !scopeValue.trim()) ||
            (scopeType === "name" && !scopeValue.trim())
          }
        >
          Next <ChevronRight className="ml-1 h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}

// ── Step 3 — Notes & submit ───────────────────────────────────────────────────

function StepNotesSubmit({
  notes,
  onNotes: setNotes,
  scheduledAt,
  onScheduledAt: setScheduledAt,
  onBack,
  onSubmit,
  submitting,
  error,
}: {
  notes: string;
  onNotes: (v: string) => void;
  scheduledAt: string;
  onScheduledAt: (v: string) => void;
  onBack: () => void;
  onSubmit: () => void;
  submitting: boolean;
  error: string | null;
}) {
  return (
    <div className="space-y-5">
      <h2 className="text-base font-semibold text-gray-800">Step 3 of 3 — Review & submit</h2>

      <div className="space-y-2">
        <label className="block text-sm font-medium text-gray-700">
          Notes for the administrator <span className="font-normal text-gray-400">(optional)</span>
        </label>
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Describe why you're requesting this restore, which content was affected, etc."
          rows={4}
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm placeholder:text-gray-400 focus:border-indigo-400 focus:outline-none"
        />
      </div>

      <div className="space-y-2">
        <label className="block text-sm font-medium text-gray-700">
          Schedule for <span className="font-normal text-gray-400">(optional — leave blank for ASAP)</span>
        </label>
        <input
          type="datetime-local"
          value={scheduledAt}
          onChange={(e) => setScheduledAt(e.target.value)}
          className="rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-indigo-400 focus:outline-none"
        />
      </div>

      {error && (
        <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}

      <div className="flex items-center justify-between">
        <Button variant="outline" onClick={onBack} disabled={submitting}>
          <ChevronLeft className="mr-1 h-4 w-4" /> Back
        </Button>
        <Button onClick={onSubmit} disabled={submitting}>
          {submitting ? "Submitting…" : "Submit restore request"}
          {!submitting && <RotateCcw className="ml-1.5 h-4 w-4" />}
        </Button>
      </div>
    </div>
  );
}

// ── Page ───────────────────────────────────────────────────────────────────────

export default function NewRestoreRequestPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const teacher = useTeacher();
  const schoolId = teacher?.school_id ?? "";

  const initialBackupId = searchParams?.get("backup_id") ?? "";

  const [step, setStep] = useState(1);
  const [backupId, setBackupId] = useState(initialBackupId);
  const [scopeType, setScopeType] = useState("full");
  const [scopeValue, setScopeValue] = useState("");
  const [sideBySide, setSideBySide] = useState(false);
  const [notes, setNotes] = useState("");
  const [scheduledAt, setScheduledAt] = useState("");
  const [submitError, setSubmitError] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["school-backups", schoolId],
    queryFn: () => schoolListBackups(schoolId),
    enabled: !!schoolId,
  });

  const backups: Backup[] = data?.backups ?? [];
  const selectedBackup = backups.find((b) => b.id === backupId);

  const mutation = useMutation({
    mutationFn: () =>
      schoolSubmitRestoreRequest(schoolId, {
        backup_id: backupId,
        scope_type: scopeType,
        scope_value: scopeValue || undefined,
        notes: notes || undefined,
        side_by_side: sideBySide,
        scheduled_at: scheduledAt
          ? new Date(scheduledAt).toISOString()
          : undefined,
      }),
    onSuccess: () => router.push("/school/restore-requests"),
    onError: (err: unknown) => {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? "Failed to submit request. Please try again.";
      setSubmitError(msg);
    },
  });

  return (
    <div className="max-w-2xl p-6">
      {/* Header */}
      <div className="mb-6 flex items-center gap-2">
        <Database className="h-6 w-6 text-indigo-600" />
        <h1 className="text-2xl font-bold text-gray-900">New Restore Request</h1>
      </div>

      {/* Step indicator */}
      <div className="mb-6 flex items-center gap-2 text-xs text-gray-400">
        {[1, 2, 3].map((s) => (
          <div key={s} className="flex items-center gap-2">
            <span
              className={`flex h-6 w-6 items-center justify-center rounded-full text-xs font-semibold ${
                s === step
                  ? "bg-indigo-600 text-white"
                  : s < step
                    ? "bg-green-500 text-white"
                    : "bg-gray-100 text-gray-400"
              }`}
            >
              {s}
            </span>
            {s < 3 && <span className="text-gray-200">—</span>}
          </div>
        ))}
      </div>

      <div className="rounded-lg border border-gray-200 bg-white p-6">
        {isLoading ? (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-16 rounded-lg" />
            ))}
          </div>
        ) : step === 1 ? (
          <StepPickBackup
            backups={backups}
            selected={backupId}
            onSelect={setBackupId}
            onNext={() => setStep(2)}
          />
        ) : step === 2 && selectedBackup ? (
          <StepConfigureScope
            backup={selectedBackup}
            scopeType={scopeType}
            scopeValue={scopeValue}
            onScopeType={setScopeType}
            onScopeValue={setScopeValue}
            sideBySide={sideBySide}
            onSideBySide={setSideBySide}
            onBack={() => setStep(1)}
            onNext={() => setStep(3)}
          />
        ) : step === 3 ? (
          <StepNotesSubmit
            notes={notes}
            onNotes={setNotes}
            scheduledAt={scheduledAt}
            onScheduledAt={setScheduledAt}
            onBack={() => setStep(2)}
            onSubmit={() => mutation.mutate()}
            submitting={mutation.isPending}
            error={submitError}
          />
        ) : null}
      </div>
    </div>
  );
}
