"use client";

import { useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTeacher } from "@/lib/hooks/useTeacher";
import {
  getRetentionDashboard,
  renewCurriculum,
  createRenewalCheckout,
  createStorageCheckout,
  assignCurriculumToGrade,
  type RetentionVersion,
} from "@/lib/api/school-admin";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Loader2,
  AlertTriangle,
  CheckCircle,
  Archive,
  RefreshCw,
  HardDrive,
  ChevronRight,
  X,
  CreditCard,
  BookMarked,
  Clock,
  Ban,
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

function StatusBadge({ status }: { status: RetentionVersion["retention_status"] }) {
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

// ── Storage strip ─────────────────────────────────────────────────────────────

function StorageStrip({
  schoolId,
  origin,
}: {
  schoolId: string;
  origin: string;
}) {
  // The backend doesn't yet expose storage_used_gb / storage_purchased_gb in the
  // retention dashboard (it's in school_storage_quotas), but we include this
  // component for the UI skeleton and the add-on checkout flow.
  const [buying, setBuying] = useState<5 | 10 | 25 | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleBuy(gb: 5 | 10 | 25) {
    if (!origin) return;
    setBuying(gb);
    setError(null);
    try {
      const { checkout_url } = await createStorageCheckout(
        schoolId,
        gb,
        `${origin}/school/retention?storage_success=1`,
        `${origin}/school/retention?storage_cancelled=1`,
      );
      window.location.href = checkout_url;
    } catch {
      setError("Could not start storage checkout. Please try again.");
      setBuying(null);
    }
  }

  return (
    <Card className="border shadow-sm">
      <CardHeader className="pb-2">
        <div className="flex items-center gap-2">
          <HardDrive className="h-4 w-4 text-gray-400" />
          <CardTitle className="text-base">Storage add-ons</CardTitle>
        </div>
      </CardHeader>
      <CardContent>
        <p className="mb-4 text-sm text-gray-500">
          Purchase additional storage for larger curriculum files and media assets.
        </p>

        {error && (
          <div className="mb-3 flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            {error}
          </div>
        )}

        <div className="flex flex-wrap gap-3">
          {([5, 10, 25] as const).map((gb) => (
            <div
              key={gb}
              className="flex flex-col items-center gap-1.5 rounded-xl border border-gray-200 p-4 min-w-[110px]"
            >
              <span className="text-lg font-bold text-gray-900">{gb} GB</span>
              <span className="text-xs text-gray-400">add-on</span>
              <Button
                size="sm"
                variant="outline"
                disabled={buying !== null}
                onClick={() => handleBuy(gb)}
                className="mt-1 w-full gap-1.5 text-xs"
              >
                {buying === gb ? (
                  <Loader2 className="h-3 w-3 animate-spin" />
                ) : (
                  <CreditCard className="h-3 w-3" />
                )}
                Buy
              </Button>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

// ── Version detail drawer ─────────────────────────────────────────────────────

function VersionDrawer({
  version,
  schoolId,
  origin,
  gradesForThisVersion,
  onClose,
  onRenewed,
}: {
  version: RetentionVersion;
  schoolId: string;
  origin: string;
  gradesForThisVersion: RetentionVersion[];
  onClose: () => void;
  onRenewed: () => void;
}) {
  const queryClient = useQueryClient();
  const [checkoutError, setCheckoutError] = useState<string | null>(null);
  const [checkingOut, setCheckingOut] = useState(false);
  const [assignGrade, setAssignGrade] = useState<number | null>(null);
  const [assignError, setAssignError] = useState<string | null>(null);
  const [assignSuccess, setAssignSuccess] = useState<string | null>(null);

  const renewMutation = useMutation({
    mutationFn: () => renewCurriculum(schoolId, version.curriculum_id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["retention", schoolId] });
      onRenewed();
    },
  });

  const assignMutation = useMutation({
    mutationFn: (grade: number) =>
      assignCurriculumToGrade(schoolId, grade, version.curriculum_id),
    onSuccess: (data) => {
      void queryClient.invalidateQueries({ queryKey: ["retention", schoolId] });
      const prev = data.previous_curriculum_id;
      setAssignSuccess(
        prev
          ? `Grade ${data.grade} reassigned. Previous: ${prev.slice(0, 8)}…`
          : `Grade ${data.grade} assigned.`,
      );
      setAssignGrade(null);
      setAssignError(null);
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
          : "Assignment failed. Please try again.";
      setAssignError(detail);
    },
  });

  async function handleCheckout() {
    if (!origin) return;
    setCheckingOut(true);
    setCheckoutError(null);
    try {
      const { checkout_url } = await createRenewalCheckout(
        schoolId,
        version.curriculum_id,
        `${origin}/school/retention?renew_success=1`,
        `${origin}/school/retention?renew_cancelled=1`,
      );
      window.location.href = checkout_url;
    } catch {
      setCheckoutError("Could not start renewal checkout. Please try again.");
      setCheckingOut(false);
    }
  }

  const canFreeRenew = version.retention_status !== "purged";
  const canAssign = version.retention_status === "active";

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-end">
      {/* backdrop */}
      <div className="absolute inset-0 bg-black/30" onClick={onClose} />

      {/* drawer */}
      <div className="relative z-10 flex h-full w-full max-w-md flex-col overflow-y-auto border-l bg-white shadow-2xl">
        {/* header */}
        <div className="flex items-start justify-between border-b p-5">
          <div>
            <div className="flex items-center gap-2">
              <BookMarked className="h-4 w-4 text-gray-400" />
              <h2 className="text-sm font-semibold text-gray-900">
                Grade {version.grade} — {version.name} ({version.year})
              </h2>
            </div>
            <div className="mt-1.5">
              <StatusBadge status={version.retention_status} />
              {version.is_assigned && (
                <span className="ml-2 inline-flex items-center gap-1 rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700">
                  <CheckCircle className="h-3 w-3" /> Assigned
                </span>
              )}
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* details */}
        <div className="space-y-5 p-5">
          {/* Date grid */}
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-lg border bg-gray-50 p-3">
              <p className="text-xs text-gray-400">Expires</p>
              <p className={cn("mt-0.5 text-sm", urgencyClass(version.days_until_expiry))}>
                {fmtDate(version.expires_at)}
              </p>
              {version.days_until_expiry !== null && (
                <p className={cn("text-xs mt-0.5", urgencyClass(version.days_until_expiry))}>
                  {version.days_until_expiry === 0
                    ? "Expires today"
                    : `${version.days_until_expiry}d left`}
                </p>
              )}
            </div>
            <div className="rounded-lg border bg-gray-50 p-3">
              <p className="text-xs text-gray-400">Grace until</p>
              <p className={cn("mt-0.5 text-sm", urgencyClass(version.days_until_purge))}>
                {fmtDate(version.grace_until)}
              </p>
              {version.days_until_purge !== null && (
                <p className={cn("text-xs mt-0.5", urgencyClass(version.days_until_purge))}>
                  {version.days_until_purge === 0
                    ? "Purge pending"
                    : `${version.days_until_purge}d until purge`}
                </p>
              )}
            </div>
            {version.renewed_at && (
              <div className="col-span-2 rounded-lg border bg-gray-50 p-3">
                <p className="text-xs text-gray-400">Last renewed</p>
                <p className="mt-0.5 text-sm text-gray-700">{fmtDate(version.renewed_at)}</p>
              </div>
            )}
          </div>

          {/* Curriculum ID */}
          <div>
            <p className="mb-1 text-xs font-medium text-gray-500">Curriculum ID</p>
            <p className="rounded border bg-gray-50 px-2 py-1.5 font-mono text-xs text-gray-600 break-all">
              {version.curriculum_id}
            </p>
          </div>

          {/* Renewal actions */}
          {version.retention_status !== "purged" && (
            <div className="space-y-2">
              <p className="text-xs font-medium text-gray-500">Renewal</p>
              {renewMutation.isSuccess ? (
                <div className="flex items-center gap-2 text-sm text-green-600">
                  <CheckCircle className="h-4 w-4 shrink-0" />
                  Renewed — expiry extended by 1 year.
                </div>
              ) : (
                <div className="flex flex-col gap-2 sm:flex-row">
                  <Button
                    size="sm"
                    variant="outline"
                    className="gap-2 border-green-300 text-green-700 hover:bg-green-50"
                    disabled={!canFreeRenew || renewMutation.isPending}
                    onClick={() => renewMutation.mutate()}
                  >
                    {renewMutation.isPending ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <RefreshCw className="h-3.5 w-3.5" />
                    )}
                    Renew (free)
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    className="gap-2"
                    disabled={checkingOut}
                    onClick={handleCheckout}
                  >
                    {checkingOut ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <CreditCard className="h-3.5 w-3.5" />
                    )}
                    Pay &amp; renew
                  </Button>
                </div>
              )}
              {checkoutError && (
                <p className="text-xs text-red-600">{checkoutError}</p>
              )}
              {renewMutation.isError && (
                <p className="text-xs text-red-600">Renewal failed. Please try again.</p>
              )}
            </div>
          )}

          {version.retention_status === "purged" && (
            <div className="flex items-center gap-2 rounded-lg border border-red-100 bg-red-50 px-3 py-2.5 text-sm text-red-700">
              <Ban className="h-4 w-4 shrink-0" />
              This version has been permanently purged and cannot be renewed. Upload a new
              curriculum JSON to rebuild.
            </div>
          )}

          {/* Grade assignment */}
          <div className="space-y-2">
            <p className="text-xs font-medium text-gray-500">Assign to grade</p>
            {!canAssign ? (
              <p className="text-xs text-gray-400">
                Only active curriculum versions can be assigned.
              </p>
            ) : (
              <>
                <p className="text-xs text-gray-500">
                  Select this version as the live content source for Grade {version.grade}.
                </p>
                {assignSuccess && (
                  <div className="flex items-center gap-2 text-sm text-green-600">
                    <CheckCircle className="h-4 w-4 shrink-0" />
                    {assignSuccess}
                  </div>
                )}
                {assignError && (
                  <p className="text-xs text-red-600">{assignError}</p>
                )}
                <Button
                  size="sm"
                  className="gap-2"
                  disabled={assignMutation.isPending || version.is_assigned}
                  onClick={() => {
                    setAssignGrade(version.grade);
                    setAssignSuccess(null);
                    setAssignError(null);
                    assignMutation.mutate(version.grade);
                  }}
                >
                  {assignMutation.isPending && assignGrade === version.grade ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <CheckCircle className="h-3.5 w-3.5" />
                  )}
                  {version.is_assigned ? "Already assigned" : `Assign to Grade ${version.grade}`}
                </Button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Summary stats row ─────────────────────────────────────────────────────────

function SummaryStats({
  active,
  unavailable,
  purged,
  total,
}: {
  active: number;
  unavailable: number;
  purged: number;
  total: number;
}) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {[
        { label: "Total", value: total, cls: "text-gray-900" },
        { label: "Active", value: active, cls: "text-green-700" },
        { label: "Unavailable", value: unavailable, cls: "text-amber-600" },
        { label: "Purged", value: purged, cls: "text-red-600" },
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

function CurriculumTable({
  curricula,
  onSelect,
}: {
  curricula: RetentionVersion[];
  onSelect: (v: RetentionVersion) => void;
}) {
  if (curricula.length === 0) {
    return (
      <div className="rounded-xl border bg-white p-8 text-center">
        <Archive className="mx-auto mb-2 h-8 w-8 text-gray-300" />
        <p className="text-sm text-gray-400">No curriculum versions found.</p>
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-xl border bg-white shadow-sm">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-gray-50 text-left text-xs font-medium text-gray-500">
              <th className="px-4 py-3">Grade</th>
              <th className="px-4 py-3">Name / Year</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Expires</th>
              <th className="px-4 py-3">Grace until</th>
              <th className="px-4 py-3">Assigned</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody className="divide-y">
            {curricula.map((v) => {
              const urgentExpiry = v.days_until_expiry !== null && v.days_until_expiry <= 30;
              const urgentPurge = v.days_until_purge !== null && v.days_until_purge <= 30;

              return (
                <tr
                  key={v.curriculum_id}
                  className={cn(
                    "transition-colors hover:bg-gray-50",
                    (urgentExpiry || urgentPurge) && "bg-amber-50/40",
                  )}
                >
                  <td className="px-4 py-3 font-mono text-xs text-gray-600">
                    G{v.grade}
                  </td>
                  <td className="px-4 py-3">
                    <p className="font-medium text-gray-900">{v.name}</p>
                    <p className="text-xs text-gray-400">{v.year}</p>
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={v.retention_status} />
                  </td>
                  <td className="px-4 py-3">
                    <div className={cn("text-xs", urgencyClass(v.days_until_expiry))}>
                      {fmtDate(v.expires_at)}
                      {v.days_until_expiry !== null && (
                        <span className="ml-1 text-gray-400">
                          ({v.days_until_expiry}d)
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className={cn("text-xs", urgencyClass(v.days_until_purge))}>
                      {fmtDate(v.grace_until)}
                      {v.days_until_purge !== null && (
                        <span className="ml-1 text-gray-400">
                          ({v.days_until_purge}d)
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    {v.is_assigned ? (
                      <span className="flex items-center gap-1 text-xs font-medium text-blue-600">
                        <CheckCircle className="h-3 w-3" /> Yes
                      </span>
                    ) : (
                      <span className="text-xs text-gray-300">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => onSelect(v)}
                      className="flex items-center gap-1 rounded px-2 py-1 text-xs text-gray-500 hover:bg-gray-100 hover:text-gray-800"
                    >
                      Details
                      <ChevronRight className="h-3 w-3" />
                    </button>
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

// ── Grade filter bar ──────────────────────────────────────────────────────────

function GradeFilterBar({
  grades,
  selected,
  onSelect,
}: {
  grades: number[];
  selected: number | null;
  onSelect: (g: number | null) => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <button
        onClick={() => onSelect(null)}
        className={cn(
          "rounded-full border px-3 py-1 text-xs font-medium transition-colors",
          selected === null
            ? "border-blue-500 bg-blue-50 text-blue-700"
            : "border-gray-200 text-gray-500 hover:border-gray-300 hover:text-gray-700",
        )}
      >
        All grades
      </button>
      {grades.map((g) => (
        <button
          key={g}
          onClick={() => onSelect(selected === g ? null : g)}
          className={cn(
            "rounded-full border px-3 py-1 text-xs font-medium transition-colors",
            selected === g
              ? "border-blue-500 bg-blue-50 text-blue-700"
              : "border-gray-200 text-gray-500 hover:border-gray-300 hover:text-gray-700",
          )}
        >
          Grade {g}
        </button>
      ))}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function RetentionPage() {
  const teacher = useTeacher();
  const schoolId = teacher?.school_id ?? "";
  const isAdmin = teacher?.role === "school_admin";

  const [origin, setOrigin] = useState("");
  useEffect(() => {
    setOrigin(window.location.origin);
  }, []);

  const [selectedVersion, setSelectedVersion] = useState<RetentionVersion | null>(null);
  const [gradeFilter, setGradeFilter] = useState<number | null>(null);
  const [statusFilter, setStatusFilter] = useState<"all" | "active" | "unavailable" | "purged">(
    "all",
  );
  const [renewedAlert, setRenewedAlert] = useState(false);

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["retention", schoolId],
    queryFn: () => getRetentionDashboard(schoolId),
    enabled: !!schoolId,
    staleTime: 30_000,
  });

  // Dismiss drawer when data refreshes after renewal
  function handleRenewed() {
    setRenewedAlert(true);
    setSelectedVersion(null);
    setTimeout(() => setRenewedAlert(false), 5000);
  }

  const allGrades = Array.from(
    new Set((data?.curricula ?? []).map((c) => c.grade)),
  ).sort((a, b) => a - b);

  const filtered = (data?.curricula ?? []).filter(
    (c) =>
      (gradeFilter === null || c.grade === gradeFilter) &&
      (statusFilter === "all" || c.retention_status === statusFilter),
  );

  // Urgent items — expiring ≤30 days or grace ≤30 days
  const urgentCount = (data?.curricula ?? []).filter(
    (c) =>
      (c.days_until_expiry !== null && c.days_until_expiry <= 30) ||
      (c.days_until_purge !== null && c.days_until_purge <= 30),
  ).length;

  if (!isAdmin) {
    return (
      <div className="p-8 text-center text-sm text-gray-400">
        Only school administrators can view the retention dashboard.
      </div>
    );
  }

  return (
    <div className="max-w-5xl space-y-6 p-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Content Retention</h1>
        <p className="mt-1 text-sm text-gray-500">
          Manage curriculum version expiry, renewal, and grade assignments.
        </p>
      </div>

      {/* Renewal success banner */}
      {renewedAlert && (
        <div className="flex items-center gap-2 rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700">
          <CheckCircle className="h-4 w-4 shrink-0" />
          Curriculum renewed — expiry extended by 1 year.
        </div>
      )}

      {/* Urgent warning */}
      {!isLoading && urgentCount > 0 && (
        <div className="flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700">
          <Clock className="h-4 w-4 shrink-0" />
          <strong>{urgentCount}</strong> curriculum version{urgentCount > 1 ? "s" : ""} expire or
          enter purge within 30 days. Review and renew them below.
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
          <button
            onClick={() => void refetch()}
            className="underline hover:no-underline"
          >
            Retry
          </button>
        </div>
      )}

      {data && (
        <>
          {/* Summary stats */}
          <SummaryStats
            total={data.total_versions}
            active={data.active_count}
            unavailable={data.unavailable_count}
            purged={data.purged_count}
          />

          {/* Storage strip */}
          <StorageStrip schoolId={schoolId} origin={origin} />

          {/* Filters */}
          <div className="flex flex-wrap items-center gap-4">
            <GradeFilterBar
              grades={allGrades}
              selected={gradeFilter}
              onSelect={setGradeFilter}
            />

            {/* Status filter */}
            <div className="flex items-center gap-1">
              {(["all", "active", "unavailable", "purged"] as const).map((s) => (
                <button
                  key={s}
                  onClick={() => setStatusFilter(s)}
                  className={cn(
                    "rounded-full border px-3 py-1 text-xs font-medium capitalize transition-colors",
                    statusFilter === s
                      ? "border-blue-500 bg-blue-50 text-blue-700"
                      : "border-gray-200 text-gray-500 hover:border-gray-300 hover:text-gray-700",
                  )}
                >
                  {s === "all" ? "All statuses" : s}
                </button>
              ))}
            </div>
          </div>

          {/* Curriculum table */}
          <CurriculumTable
            curricula={filtered}
            onSelect={setSelectedVersion}
          />

          {filtered.length > 0 && (
            <p className="text-xs text-gray-400">
              Showing {filtered.length} of {data.total_versions} version
              {data.total_versions !== 1 ? "s" : ""}.
            </p>
          )}
        </>
      )}

      {/* Version detail drawer */}
      {selectedVersion && (
        <VersionDrawer
          version={selectedVersion}
          schoolId={schoolId}
          origin={origin}
          gradesForThisVersion={(data?.curricula ?? []).filter(
            (c) => c.grade === selectedVersion.grade,
          )}
          onClose={() => setSelectedVersion(null)}
          onRenewed={handleRenewed}
        />
      )}
    </div>
  );
}
