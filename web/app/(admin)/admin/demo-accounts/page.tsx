"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  getDemoAccounts,
  extendDemoAccount,
  revokeDemoAccount,
  adminResendDemoVerification,
  type DemoAccountItem,
} from "@/lib/api/admin";
import { useAdmin, hasPermission } from "@/lib/hooks/useAdmin";
import {
  ShieldOff,
  FlaskConical,
  Clock,
  MailCheck,
  CheckCircle2,
  XCircle,
  Hourglass,
  Mail,
} from "lucide-react";

const PAGE_SIZE = 20;

const STATUS_FILTERS = [
  { value: "", label: "All" },
  { value: "pending", label: "Pending" },
  { value: "verified", label: "Active" },
  { value: "expired", label: "Expired" },
  { value: "revoked", label: "Revoked" },
] as const;

const STATUS_META: Record<
  DemoAccountItem["request_status"],
  { label: string; icon: React.ReactNode; className: string }
> = {
  pending: {
    label: "Pending",
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

function StatusBadge({ status }: { status: DemoAccountItem["request_status"] }) {
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

// ── Extend modal ──────────────────────────────────────────────────────────────

function ExtendModal({
  item,
  onClose,
  onDone,
}: {
  item: DemoAccountItem;
  onClose: () => void;
  onDone: () => void;
}) {
  const [hours, setHours] = useState(24);
  const [submitting, setSubmitting] = useState(false);

  async function handleExtend() {
    if (!item.account_id) return;
    setSubmitting(true);
    try {
      await extendDemoAccount(item.account_id, hours);
      toast.success(`Extended demo for ${item.email} by ${hours}h`);
      onDone();
    } catch {
      toast.error("Failed to extend demo account");
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-sm rounded-xl bg-white p-6 shadow-xl">
        <h2 className="mb-1 text-base font-semibold text-gray-900">Extend demo</h2>
        <p className="mb-4 text-sm break-all text-gray-500">{item.email}</p>
        <label className="mb-1 block text-xs font-medium text-gray-700">
          Hours to add (1–168)
        </label>
        <input
          type="number"
          min={1}
          max={168}
          value={hours}
          onChange={(e) => setHours(Math.max(1, Math.min(168, Number(e.target.value))))}
          className="mb-4 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:outline-none"
        />
        <div className="flex gap-2">
          <button
            onClick={handleExtend}
            disabled={submitting}
            className="flex-1 rounded-lg bg-indigo-600 py-2 text-sm font-medium text-white transition-colors hover:bg-indigo-700 disabled:opacity-50"
          >
            {submitting ? "Extending…" : "Extend"}
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

// ── Revoke confirm ────────────────────────────────────────────────────────────

function RevokeModal({
  item,
  onClose,
  onDone,
}: {
  item: DemoAccountItem;
  onClose: () => void;
  onDone: () => void;
}) {
  const [submitting, setSubmitting] = useState(false);

  async function handleRevoke() {
    if (!item.account_id) return;
    setSubmitting(true);
    try {
      await revokeDemoAccount(item.account_id);
      toast.success(`Revoked demo for ${item.email}`);
      onDone();
    } catch {
      toast.error("Failed to revoke demo account");
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-sm rounded-xl bg-white p-6 shadow-xl">
        <h2 className="mb-1 text-base font-semibold text-gray-900">Revoke demo?</h2>
        <p className="mb-1 text-sm break-all text-gray-500">{item.email}</p>
        <p className="mb-4 text-sm text-gray-500">
          This immediately ends their demo session. This cannot be undone.
        </p>
        <div className="flex gap-2">
          <button
            onClick={handleRevoke}
            disabled={submitting}
            className="flex-1 rounded-lg bg-red-600 py-2 text-sm font-medium text-white transition-colors hover:bg-red-700 disabled:opacity-50"
          >
            {submitting ? "Revoking…" : "Revoke"}
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

// ── Row actions ───────────────────────────────────────────────────────────────

function RowActions({
  item,
  onRefresh,
}: {
  item: DemoAccountItem;
  onRefresh: () => void;
}) {
  const [modal, setModal] = useState<"extend" | "revoke" | null>(null);
  const [resending, setResending] = useState(false);

  async function handleResend() {
    setResending(true);
    try {
      await adminResendDemoVerification(item.request_id);
      toast.success(`Verification re-sent to ${item.email}`);
    } catch {
      toast.error("Failed to resend verification email");
    } finally {
      setResending(false);
    }
  }

  return (
    <>
      <div className="flex items-center gap-1.5">
        {item.verification_pending && (
          <button
            onClick={handleResend}
            disabled={resending}
            title="Resend verification email"
            className="flex items-center gap-1 rounded-md bg-blue-50 px-2 py-1 text-xs font-medium text-blue-600 transition-colors hover:bg-blue-100 disabled:opacity-50"
          >
            <MailCheck className="h-3 w-3" />
            {resending ? "Sending…" : "Resend"}
          </button>
        )}
        {item.account_id && item.request_status === "verified" && (
          <>
            <button
              onClick={() => setModal("extend")}
              title="Extend demo access"
              className="flex items-center gap-1 rounded-md bg-indigo-50 px-2 py-1 text-xs font-medium text-indigo-600 transition-colors hover:bg-indigo-100"
            >
              <Clock className="h-3 w-3" />
              Extend
            </button>
            <button
              onClick={() => setModal("revoke")}
              title="Revoke demo access"
              className="rounded-md bg-red-50 px-2 py-1 text-xs font-medium text-red-600 transition-colors hover:bg-red-100"
            >
              Revoke
            </button>
          </>
        )}
      </div>

      {modal === "extend" && (
        <ExtendModal
          item={item}
          onClose={() => setModal(null)}
          onDone={() => {
            setModal(null);
            onRefresh();
          }}
        />
      )}
      {modal === "revoke" && (
        <RevokeModal
          item={item}
          onClose={() => setModal(null)}
          onDone={() => {
            setModal(null);
            onRefresh();
          }}
        />
      )}
    </>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function AdminDemoAccountsPage() {
  const admin = useAdmin();
  const qc = useQueryClient();
  const [statusFilter, setStatusFilter] = useState("");
  const [emailSearch, setEmailSearch] = useState("");
  const [emailInput, setEmailInput] = useState("");
  const [page, setPage] = useState(1);

  const { data, isLoading } = useQuery({
    queryKey: ["admin", "demo-accounts", page, statusFilter, emailSearch],
    queryFn: () =>
      getDemoAccounts(
        page,
        PAGE_SIZE,
        statusFilter || undefined,
        emailSearch || undefined,
      ),
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
          Managing demo accounts requires <strong>product_admin</strong> or higher.
        </p>
      </div>
    );
  }

  function refresh() {
    qc.invalidateQueries({ queryKey: ["admin", "demo-accounts"] });
  }

  function applyEmailSearch(e: React.FormEvent) {
    e.preventDefault();
    setEmailSearch(emailInput.trim());
    setPage(1);
  }

  return (
    <div className="mx-auto max-w-6xl p-8">
      <h1 className="mb-1 text-2xl font-bold text-gray-900">Demo Accounts</h1>
      <p className="mb-6 text-sm text-gray-500">
        Manage demo student requests and active demo sessions.
      </p>

      {/* Filters */}
      <div className="mb-6 flex flex-wrap items-center gap-3">
        {/* Status tabs */}
        <div className="flex gap-1.5">
          {STATUS_FILTERS.map((f) => (
            <button
              key={f.value}
              onClick={() => {
                setStatusFilter(f.value);
                setPage(1);
              }}
              className={`rounded-full px-3 py-1.5 text-sm font-medium transition-colors ${
                statusFilter === f.value
                  ? "bg-indigo-600 text-white"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>

        {/* Email search */}
        <form onSubmit={applyEmailSearch} className="ml-auto flex gap-2">
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
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 8 }).map((_, i) => (
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
                    Email
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">
                    Status
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">
                    Expires
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">
                    Extended
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">
                    Revoked
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {data.items.map((item) => (
                  <tr key={item.request_id} className="hover:bg-gray-50">
                    <td className="max-w-[200px] truncate px-4 py-3 font-medium text-gray-900">
                      {item.email}
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={item.request_status} />
                    </td>
                    <td className="px-4 py-3 text-gray-500">
                      {item.expires_at ? new Date(item.expires_at).toLocaleString() : "—"}
                    </td>
                    <td className="px-4 py-3 text-gray-500">
                      {item.extended_at
                        ? new Date(item.extended_at).toLocaleString()
                        : "—"}
                    </td>
                    <td className="px-4 py-3 text-gray-500">
                      {item.revoked_at ? new Date(item.revoked_at).toLocaleString() : "—"}
                    </td>
                    <td className="px-4 py-3">
                      <RowActions item={item} onRefresh={refresh} />
                    </td>
                  </tr>
                ))}
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
          <p className="text-sm">No demo accounts found.</p>
        </div>
      )}
    </div>
  );
}
