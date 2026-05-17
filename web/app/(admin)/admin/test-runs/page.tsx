"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { getTestRuns, deleteTestRunByEmail, type TestRunItem } from "@/lib/api/admin";
import { useAdmin, hasPermission } from "@/lib/hooks/useAdmin";
import {
  ShieldOff,
  FlaskConical,
  CheckCircle2,
  XCircle,
  Hourglass,
  Mail,
  Trash2,
} from "lucide-react";

const PAGE_SIZE = 50;

const STATUS_META: Record<
  TestRunItem["status"],
  { label: string; icon: React.ReactNode; className: string }
> = {
  pending: {
    label: "Awaiting verification",
    icon: <Mail className="h-3 w-3 shrink-0" aria-hidden="true" />,
    className: "bg-yellow-100 text-yellow-700",
  },
  verified: {
    label: "Active",
    icon: <CheckCircle2 className="h-3 w-3 shrink-0" aria-hidden="true" />,
    className: "bg-green-100 text-green-700",
  },
  expired: {
    label: "Expired",
    icon: <Hourglass className="h-3 w-3 shrink-0" aria-hidden="true" />,
    className: "bg-gray-100 text-gray-500",
  },
  revoked: {
    label: "Revoked",
    icon: <XCircle className="h-3 w-3 shrink-0" aria-hidden="true" />,
    className: "bg-red-100 text-red-600",
  },
};

function StatusBadge({ status }: { status: TestRunItem["status"] }) {
  const { label, icon, className } = STATUS_META[status];
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${className}`}
    >
      {icon}
      {label}
    </span>
  );
}

/**
 * Earliest expiry across the student + teacher accounts. The student demo TTL
 * (24h) is shorter than the teacher TTL (48h), so this surfaces the binding
 * constraint on how long the visitor can keep exploring.
 */
function earliestExpiry(item: TestRunItem): string | null {
  if (item.status !== "verified") {
    return item.verification_expires_at;
  }
  const candidates = [item.student_expires_at, item.teacher_expires_at].filter(
    Boolean,
  ) as string[];
  if (candidates.length === 0) return null;
  return candidates.sort()[0]; // ISO strings sort lexicographically
}

function formatRemaining(iso: string | null): string {
  if (!iso) return "—";
  const ms = new Date(iso).getTime() - Date.now();
  if (ms <= 0) return "expired";
  const hours = Math.floor(ms / (1000 * 60 * 60));
  if (hours >= 24) return `${Math.floor(hours / 24)}d ${hours % 24}h`;
  if (hours >= 1) return `${hours}h ${Math.floor((ms / (1000 * 60)) % 60)}m`;
  const mins = Math.max(1, Math.floor(ms / (1000 * 60)));
  return `${mins}m`;
}

// ── Reset (delete) confirm modal ─────────────────────────────────────────────

function ResetModal({
  item,
  onClose,
  onDone,
}: {
  item: TestRunItem;
  onClose: () => void;
  onDone: () => void;
}) {
  const [submitting, setSubmitting] = useState(false);

  async function handleReset() {
    setSubmitting(true);
    try {
      const result = await deleteTestRunByEmail(item.email);
      const total =
        result.student_requests_deleted +
        result.teacher_requests_deleted +
        result.students_deleted +
        result.teachers_deleted;
      toast.success(`Reset ${item.email} — ${total} rows cleared`);
      onDone();
    } catch {
      toast.error("Failed to reset test run");
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-sm rounded-xl bg-white p-6 shadow-xl">
        <h2 className="mb-1 text-base font-semibold text-gray-900">
          Reset this test run?
        </h2>
        <p className="mb-1 text-sm break-all text-gray-700">{item.email}</p>
        <p className="mb-4 text-sm text-gray-500">
          Removes both the teacher and student demo accounts and their request history so
          this email can submit a fresh test run. This cannot be undone.
        </p>
        <div className="flex gap-2">
          <button
            onClick={handleReset}
            disabled={submitting}
            className="flex-1 rounded-lg bg-red-600 py-2 text-sm font-medium text-white transition-colors hover:bg-red-700 disabled:opacity-50"
          >
            {submitting ? "Resetting…" : "Reset"}
          </button>
          <button
            onClick={onClose}
            className="flex-1 rounded-lg border border-gray-200 py-2 text-sm font-medium text-gray-600 transition-colors hover:bg-gray-50"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function AdminTestRunsPage() {
  const admin = useAdmin();
  const qc = useQueryClient();
  const [emailInput, setEmailInput] = useState("");
  const [emailSearch, setEmailSearch] = useState("");
  const [page, setPage] = useState(1);
  const [resetTarget, setResetTarget] = useState<TestRunItem | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["admin", "test-runs", page, emailSearch],
    queryFn: () => getTestRuns(page, PAGE_SIZE, emailSearch || undefined),
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
          Managing test runs requires <strong>product_admin</strong> or higher.
        </p>
      </div>
    );
  }

  function refresh() {
    qc.invalidateQueries({ queryKey: ["admin", "test-runs"] });
  }

  function applyEmailSearch(e: React.FormEvent) {
    e.preventDefault();
    setEmailSearch(emailInput.trim());
    setPage(1);
  }

  return (
    <div className="mx-auto max-w-6xl p-8">
      <h1 className="mb-1 text-2xl font-bold text-gray-900">Test Runs</h1>
      <p className="mb-6 text-sm text-gray-500">
        Visitors who submitted the &ldquo;Try a test run&rdquo; form. Each row provisions
        both a teacher and a student demo account. Reset a row to free the email for
        re-submission.
      </p>

      {/* Email search */}
      <form
        onSubmit={applyEmailSearch}
        className="mb-6 flex flex-wrap items-center gap-2"
      >
        <input
          type="text"
          placeholder="Search by email…"
          value={emailInput}
          onChange={(e) => setEmailInput(e.target.value)}
          className="rounded-lg border border-gray-200 px-3 py-1.5 text-sm focus:ring-2 focus:ring-indigo-500 focus:outline-none"
        />
        <button
          type="submit"
          className="rounded-lg bg-gray-100 px-3 py-1.5 text-sm font-medium text-gray-600 transition-colors hover:bg-gray-200"
        >
          Search
        </button>
        {emailSearch && (
          <button
            type="button"
            onClick={() => {
              setEmailInput("");
              setEmailSearch("");
              setPage(1);
            }}
            className="rounded-lg bg-gray-100 px-3 py-1.5 text-sm text-gray-500 transition-colors hover:bg-gray-200"
          >
            Clear
          </button>
        )}
      </form>

      {/* Table */}
      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-14 animate-pulse rounded-lg bg-gray-100" />
          ))}
        </div>
      ) : data && data.items.length > 0 ? (
        <>
          <p className="mb-2 text-xs text-gray-400">
            {data.total} record{data.total !== 1 ? "s" : ""}
          </p>
          <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 bg-gray-50">
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">
                    Name
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">
                    Email
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">
                    Requested
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">
                    Status
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">
                    Expires in
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">
                    Action
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {data.items.map((item) => {
                  const expiry = earliestExpiry(item);
                  return (
                    <tr key={item.student_email} className="hover:bg-gray-50">
                      <td className="px-4 py-3 font-medium text-gray-900">
                        {item.name ?? <span className="text-gray-400">—</span>}
                      </td>
                      <td className="max-w-[260px] truncate px-4 py-3 text-gray-700">
                        {item.email}
                      </td>
                      <td className="px-4 py-3 text-gray-500">
                        {new Date(item.requested_at).toLocaleString()}
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge status={item.status} />
                      </td>
                      <td className="px-4 py-3 text-gray-500">
                        {formatRemaining(expiry)}
                      </td>
                      <td className="px-4 py-3">
                        <button
                          onClick={() => setResetTarget(item)}
                          className="flex items-center gap-1 rounded-md bg-red-50 px-2 py-1 text-xs font-medium text-red-600 transition-colors hover:bg-red-100"
                          title="Delete both accounts so this email can re-request"
                        >
                          <Trash2 className="h-3 w-3" />
                          Reset
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
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
              disabled={(data.items.length ?? 0) < PAGE_SIZE}
              onClick={() => setPage(page + 1)}
              className="rounded-lg bg-gray-100 px-3 py-1.5 text-sm text-gray-600 transition-colors hover:bg-gray-200 disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </>
      ) : (
        <div className="py-20 text-center text-gray-400">
          <FlaskConical className="mx-auto mb-3 h-10 w-10 opacity-40" />
          <p className="text-sm font-medium text-gray-600">
            {emailSearch ? "No test runs match your search." : "No test runs yet."}
          </p>
          {!emailSearch && (
            <p className="mt-1 text-xs text-gray-400">
              Visitors appear here after they submit the &ldquo;Try a test run&rdquo; form
              on the demo home page.
            </p>
          )}
        </div>
      )}

      {resetTarget && (
        <ResetModal
          item={resetTarget}
          onClose={() => setResetTarget(null)}
          onDone={() => {
            setResetTarget(null);
            refresh();
          }}
        />
      )}
    </div>
  );
}
