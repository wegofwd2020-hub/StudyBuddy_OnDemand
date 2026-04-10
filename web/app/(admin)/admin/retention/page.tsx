"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getAdminRetentionDashboard,
  adminCurriculumAction,
  type AdminRetentionItem,
} from "@/lib/api/admin";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Loader2,
  AlertTriangle,
  CheckCircle,
  Archive,
  RefreshCw,
  ChevronRight,
  X,
  Clock,
  School,
  Trash2,
  Ban,
  Search,
} from "lucide-react";
import { cn } from "@/lib/utils";

// ── Helpers ────────────────────────────────────────────────────────────────────

function fmtDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function urgencyClass(days: number | null): string {
  if (days === null) return "";
  if (days <= 7) return "text-red-600 font-semibold";
  if (days <= 30) return "text-amber-600 font-medium";
  return "text-gray-700";
}

// ── Status badge ──────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: AdminRetentionItem["retention_status"] }) {
  const map = {
    active: { label: "Active", cls: "bg-green-100 text-green-700" },
    unavailable: { label: "Unavailable", cls: "bg-amber-100 text-amber-700" },
    purged: { label: "Purged", cls: "bg-red-100 text-red-600" },
  } as const;
  const { label, cls } = map[status] ?? { label: status, cls: "bg-gray-100 text-gray-500" };
  return (
    <span className={cn("inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium", cls)}>
      {label}
    </span>
  );
}

// ── Confirm-action modal ──────────────────────────────────────────────────────

type ActionType = "renew" | "force_expire" | "force_delete";

const ACTION_META: Record<ActionType, { label: string; description: string; confirmWord?: string; danger: boolean }> = {
  renew: {
    label: "Renew",
    description: "Extend this curriculum's expiry by 1 year and reset status to active.",
    danger: false,
  },
  force_expire: {
    label: "Force expire",
    description: "Immediately mark this curriculum unavailable with a 180-day grace period. Students lose access now.",
    danger: true,
  },
  force_delete: {
    label: "Force delete",
    description: "Permanently delete all content rows for this curriculum. This cannot be undone.",
    confirmWord: "DELETE",
    danger: true,
  },
};

function ActionModal({
  item,
  action,
  onClose,
  onConfirm,
  isPending,
}: {
  item: AdminRetentionItem;
  action: ActionType;
  onClose: () => void;
  onConfirm: (reason: string) => void;
  isPending: boolean;
}) {
  const [reason, setReason] = useState("");
  const [confirm, setConfirm] = useState("");
  const meta = ACTION_META[action];
  const needsWord = !!meta.confirmWord;
  const canSubmit = reason.trim().length >= 5 && (!needsWord || confirm === meta.confirmWord);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-md rounded-xl border bg-white p-6 shadow-2xl">
        <div className="mb-4 flex items-start justify-between gap-3">
          <div className="flex items-center gap-2">
            {meta.danger ? (
              <AlertTriangle className="h-5 w-5 shrink-0 text-red-500" />
            ) : (
              <RefreshCw className="h-5 w-5 shrink-0 text-green-500" />
            )}
            <h2 className="text-base font-semibold text-gray-900">{meta.label}</h2>
          </div>
          <button onClick={onClose} className="rounded p-1 text-gray-400 hover:bg-gray-100">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="mb-4 rounded-lg border bg-gray-50 p-3 text-sm text-gray-700">
          <p className="font-medium">{item.school_name} — Grade {item.grade}</p>
          <p className="text-xs text-gray-500 mt-0.5">{item.name} ({item.year}) · {item.curriculum_id.slice(0, 16)}…</p>
        </div>

        <p className="mb-4 text-sm text-gray-600">{meta.description}</p>

        <div className="space-y-3">
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-700">
              Reason <span className="text-red-500">*</span>
            </label>
            <textarea
              rows={2}
              className="w-full rounded border px-3 py-2 text-sm text-gray-800 placeholder:text-gray-400 focus:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-300"
              placeholder="School requested removal via support ticket #12345…"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
            {reason.trim().length > 0 && reason.trim().length < 5 && (
              <p className="mt-0.5 text-xs text-red-500">Reason must be at least 5 characters.</p>
            )}
          </div>

          {needsWord && (
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-700">
                Type <strong>{meta.confirmWord}</strong> to confirm
              </label>
              <input
                type="text"
                className="w-full rounded border px-3 py-2 text-sm font-mono text-gray-800 placeholder:text-gray-400 focus:border-red-400 focus:outline-none focus:ring-1 focus:ring-red-300"
                placeholder={meta.confirmWord}
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
              />
            </div>
          )}
        </div>

        <div className="mt-5 flex justify-end gap-2">
          <Button variant="outline" size="sm" onClick={onClose} disabled={isPending}>
            Cancel
          </Button>
          <Button
            size="sm"
            disabled={!canSubmit || isPending}
            className={cn(
              "gap-2",
              meta.danger
                ? "bg-red-600 text-white hover:bg-red-700"
                : "bg-green-600 text-white hover:bg-green-700",
            )}
            onClick={() => onConfirm(reason.trim())}
          >
            {isPending && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
            {meta.label}
          </Button>
        </div>
      </div>
    </div>
  );
}

// ── Row action menu ───────────────────────────────────────────────────────────

function RowActions({
  item,
  onAction,
}: {
  item: AdminRetentionItem;
  onAction: (item: AdminRetentionItem, action: ActionType) => void;
}) {
  const [open, setOpen] = useState(false);

  const actions: { action: ActionType; label: string; icon: React.ReactNode; disabled?: boolean }[] = [
    {
      action: "renew",
      label: "Renew",
      icon: <RefreshCw className="h-3.5 w-3.5" />,
      disabled: item.retention_status === "purged",
    },
    {
      action: "force_expire",
      label: "Force expire",
      icon: <Ban className="h-3.5 w-3.5 text-amber-500" />,
      disabled: item.retention_status !== "active",
    },
    {
      action: "force_delete",
      label: "Force delete",
      icon: <Trash2 className="h-3.5 w-3.5 text-red-500" />,
    },
  ];

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1 rounded px-2 py-1 text-xs text-gray-500 hover:bg-gray-100 hover:text-gray-800"
      >
        Actions
        <ChevronRight className={cn("h-3 w-3 transition-transform", open && "rotate-90")} />
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute right-0 z-20 mt-1 w-36 overflow-hidden rounded-lg border bg-white shadow-lg">
            {actions.map(({ action, label, icon, disabled }) => (
              <button
                key={action}
                disabled={disabled}
                onClick={() => {
                  setOpen(false);
                  onAction(item, action);
                }}
                className={cn(
                  "flex w-full items-center gap-2 px-3 py-2 text-left text-xs transition-colors",
                  disabled
                    ? "cursor-not-allowed text-gray-300"
                    : "text-gray-700 hover:bg-gray-50",
                )}
              >
                {icon}
                {label}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

// ── Summary stat tiles ────────────────────────────────────────────────────────

function SummaryTiles({
  total,
  active,
  unavailable,
  purged,
  expiringSoon,
}: {
  total: number;
  active: number;
  unavailable: number;
  purged: number;
  expiringSoon: number;
}) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
      {[
        { label: "Total", value: total, cls: "text-gray-900" },
        { label: "Active", value: active, cls: "text-green-700" },
        { label: "Unavailable", value: unavailable, cls: "text-amber-600" },
        { label: "Purged", value: purged, cls: "text-red-600" },
        { label: "Expiring ≤30d", value: expiringSoon, cls: expiringSoon > 0 ? "text-red-600" : "text-gray-400" },
      ].map(({ label, value, cls }) => (
        <div key={label} className="rounded-xl border bg-white p-4 text-center shadow-sm">
          <p className={cn("text-2xl font-bold", cls)}>{value}</p>
          <p className="mt-0.5 text-xs text-gray-400">{label}</p>
        </div>
      ))}
    </div>
  );
}

// ── Curriculum table ──────────────────────────────────────────────────────────

function RetentionTable({
  curricula,
  onAction,
}: {
  curricula: AdminRetentionItem[];
  onAction: (item: AdminRetentionItem, action: ActionType) => void;
}) {
  if (curricula.length === 0) {
    return (
      <div className="rounded-xl border bg-white p-10 text-center">
        <Archive className="mx-auto mb-2 h-8 w-8 text-gray-300" />
        <p className="text-sm text-gray-400">No curriculum versions match the current filters.</p>
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-xl border bg-white shadow-sm">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-gray-50 text-left text-xs font-medium text-gray-500">
              <th className="px-4 py-3">School</th>
              <th className="px-4 py-3">Grade</th>
              <th className="px-4 py-3">Curriculum</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Expires</th>
              <th className="px-4 py-3">Grace until</th>
              <th className="px-4 py-3">Assigned</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody className="divide-y">
            {curricula.map((item) => {
              const urgentExpiry = item.days_until_expiry !== null && item.days_until_expiry <= 30;
              const urgentPurge = item.days_until_purge !== null && item.days_until_purge <= 30;

              return (
                <tr
                  key={item.curriculum_id}
                  className={cn(
                    "transition-colors hover:bg-gray-50",
                    (urgentExpiry || urgentPurge) && "bg-amber-50/40",
                  )}
                >
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1.5">
                      <School className="h-3.5 w-3.5 shrink-0 text-gray-300" />
                      <div>
                        <p className="font-medium text-gray-900 leading-tight">{item.school_name}</p>
                        <p className="text-xs text-gray-400 leading-tight">{item.contact_email}</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-gray-600">G{item.grade}</td>
                  <td className="px-4 py-3">
                    <p className="font-medium text-gray-900">{item.name}</p>
                    <p className="text-xs text-gray-400">{item.year}</p>
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={item.retention_status} />
                  </td>
                  <td className="px-4 py-3">
                    <div className={cn("text-xs", urgencyClass(item.days_until_expiry))}>
                      {fmtDate(item.expires_at)}
                      {item.days_until_expiry !== null && (
                        <span className="ml-1 text-gray-400">({item.days_until_expiry}d)</span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className={cn("text-xs", urgencyClass(item.days_until_purge))}>
                      {fmtDate(item.grace_until)}
                      {item.days_until_purge !== null && (
                        <span className="ml-1 text-gray-400">({item.days_until_purge}d)</span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    {item.is_assigned ? (
                      <span className="flex items-center gap-1 text-xs font-medium text-blue-600">
                        <CheckCircle className="h-3 w-3" /> Yes
                      </span>
                    ) : (
                      <span className="text-xs text-gray-300">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <RowActions item={item} onAction={onAction} />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function AdminRetentionPage() {
  const queryClient = useQueryClient();

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [schoolSearch, setSchoolSearch] = useState("");
  const [gradeFilter, setGradeFilter] = useState<number | null>(null);

  // Action modal state
  const [pendingAction, setPendingAction] = useState<{
    item: AdminRetentionItem;
    action: ActionType;
  } | null>(null);

  // Toast state
  const [toast, setToast] = useState<{ msg: string; ok: boolean } | null>(null);

  function showToast(msg: string, ok: boolean) {
    setToast({ msg, ok });
    setTimeout(() => setToast(null), 5000);
  }

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["admin-retention"],
    queryFn: () => getAdminRetentionDashboard(),
    staleTime: 30_000,
  });

  const actionMutation = useMutation({
    mutationFn: ({ item, action, reason }: { item: AdminRetentionItem; action: ActionType; reason: string }) =>
      adminCurriculumAction(item.school_id, item.curriculum_id, action, reason),
    onSuccess: (res) => {
      void queryClient.invalidateQueries({ queryKey: ["admin-retention"] });
      setPendingAction(null);
      showToast(res.detail, true);
    },
    onError: (err: unknown) => {
      const detail =
        err != null &&
        typeof err === "object" &&
        "response" in err &&
        err.response != null &&
        typeof err.response === "object" &&
        "data" in err.response &&
        err.response.data != null &&
        typeof err.response.data === "object" &&
        "detail" in err.response.data
          ? String((err.response.data as { detail: unknown }).detail)
          : "Action failed. Please try again.";
      setPendingAction(null);
      showToast(detail, false);
    },
  });

  // Client-side filtering
  const filtered = (data?.curricula ?? []).filter((c) => {
    const matchStatus = statusFilter === "all" || c.retention_status === statusFilter;
    const matchSchool =
      !schoolSearch ||
      c.school_name.toLowerCase().includes(schoolSearch.toLowerCase()) ||
      c.contact_email.toLowerCase().includes(schoolSearch.toLowerCase());
    const matchGrade = gradeFilter === null || c.grade === gradeFilter;
    return matchStatus && matchSchool && matchGrade;
  });

  const allGrades = Array.from(new Set((data?.curricula ?? []).map((c) => c.grade))).sort(
    (a, b) => a - b,
  );

  return (
    <div className="max-w-7xl space-y-6 p-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Retention Monitor</h1>
        <p className="mt-1 text-sm text-gray-500">
          Platform-wide view of curriculum version lifecycle across all schools.
        </p>
      </div>

      {/* Toast */}
      {toast && (
        <div
          className={cn(
            "flex items-center gap-2 rounded-lg border px-4 py-3 text-sm",
            toast.ok
              ? "border-green-200 bg-green-50 text-green-700"
              : "border-red-200 bg-red-50 text-red-700",
          )}
        >
          {toast.ok ? (
            <CheckCircle className="h-4 w-4 shrink-0" />
          ) : (
            <AlertTriangle className="h-4 w-4 shrink-0" />
          )}
          {toast.msg}
        </div>
      )}

      {/* Urgent banner */}
      {data && data.summary.expiring_soon > 0 && (
        <div className="flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700">
          <Clock className="h-4 w-4 shrink-0" />
          <strong>{data.summary.expiring_soon}</strong> curriculum version
          {data.summary.expiring_soon > 1 ? "s" : ""} across all schools expire within 30 days.
        </div>
      )}

      {/* Loading */}
      {isLoading && (
        <div className="flex items-center gap-2 text-sm text-gray-400">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading retention data…
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          Failed to load retention data.{" "}
          <button onClick={() => void refetch()} className="underline hover:no-underline">
            Retry
          </button>
        </div>
      )}

      {data && (
        <>
          {/* Summary */}
          <SummaryTiles
            total={data.summary.total}
            active={data.summary.active}
            unavailable={data.summary.unavailable}
            purged={data.summary.purged}
            expiringSoon={data.summary.expiring_soon}
          />

          {/* Filters */}
          <Card className="border shadow-sm">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-gray-600">Filters</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap items-center gap-4">
                {/* School search */}
                <div className="flex items-center gap-2 rounded-lg border px-3 py-1.5 text-sm">
                  <Search className="h-3.5 w-3.5 text-gray-400" />
                  <input
                    type="text"
                    placeholder="Search school…"
                    className="w-40 border-none bg-transparent text-sm text-gray-800 placeholder:text-gray-400 focus:outline-none"
                    value={schoolSearch}
                    onChange={(e) => setSchoolSearch(e.target.value)}
                  />
                </div>

                {/* Status pills */}
                <div className="flex flex-wrap gap-1">
                  {(["all", "active", "unavailable", "purged"] as const).map((s) => (
                    <button
                      key={s}
                      onClick={() => setStatusFilter(s)}
                      className={cn(
                        "rounded-full border px-3 py-1 text-xs font-medium capitalize transition-colors",
                        statusFilter === s
                          ? "border-indigo-500 bg-indigo-50 text-indigo-700"
                          : "border-gray-200 text-gray-500 hover:border-gray-300 hover:text-gray-700",
                      )}
                    >
                      {s === "all" ? "All statuses" : s}
                    </button>
                  ))}
                </div>

                {/* Grade pills */}
                {allGrades.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    <button
                      onClick={() => setGradeFilter(null)}
                      className={cn(
                        "rounded-full border px-3 py-1 text-xs font-medium transition-colors",
                        gradeFilter === null
                          ? "border-indigo-500 bg-indigo-50 text-indigo-700"
                          : "border-gray-200 text-gray-500 hover:border-gray-300 hover:text-gray-700",
                      )}
                    >
                      All grades
                    </button>
                    {allGrades.map((g) => (
                      <button
                        key={g}
                        onClick={() => setGradeFilter(gradeFilter === g ? null : g)}
                        className={cn(
                          "rounded-full border px-3 py-1 text-xs font-medium transition-colors",
                          gradeFilter === g
                            ? "border-indigo-500 bg-indigo-50 text-indigo-700"
                            : "border-gray-200 text-gray-500 hover:border-gray-300 hover:text-gray-700",
                        )}
                      >
                        G{g}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Table */}
          <RetentionTable curricula={filtered} onAction={(item, action) => setPendingAction({ item, action })} />

          <p className="text-xs text-gray-400">
            Showing {filtered.length} of {data.summary.total} version
            {data.summary.total !== 1 ? "s" : ""} across all schools. Sorted by urgency.
          </p>
        </>
      )}

      {/* Action modal */}
      {pendingAction && (
        <ActionModal
          item={pendingAction.item}
          action={pendingAction.action}
          onClose={() => setPendingAction(null)}
          onConfirm={(reason) =>
            actionMutation.mutate({ item: pendingAction.item, action: pendingAction.action, reason })
          }
          isPending={actionMutation.isPending}
        />
      )}
    </div>
  );
}
