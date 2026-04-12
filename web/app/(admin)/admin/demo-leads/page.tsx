"use client";

/**
 * /admin/demo-leads
 *
 * PLAT-ADMIN console for managing self-serve demo tour requests.
 * Lists leads with status filter; approve (generates personalised tour URLs)
 * or reject with optional reason.
 *
 * Requires: sb_admin_token with plat_admin role (demo:manage permission).
 */

import { useState } from "react";
import {
  listDemoLeads,
  approveDemoLead,
  rejectDemoLead,
  type DemoLeadItem,
  type DemoLeadApproveResponse,
} from "@/lib/api/admin";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  CheckCircle,
  XCircle,
  Clock,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Copy,
  Check,
} from "lucide-react";

type StatusFilter = "all" | "pending" | "approved" | "rejected";

function StatusBadge({ status }: { status: DemoLeadItem["status"] }) {
  if (status === "pending")
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-yellow-100 px-2.5 py-0.5 text-xs font-medium text-yellow-800">
        <Clock className="h-3 w-3" />
        Pending
      </span>
    );
  if (status === "approved")
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-medium text-green-800">
        <CheckCircle className="h-3 w-3" />
        Approved
      </span>
    );
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-medium text-red-800">
      <XCircle className="h-3 w-3" />
      Rejected
    </span>
  );
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={async () => {
        await navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      }}
      className="ml-1 text-gray-400 hover:text-gray-600"
      title="Copy URL"
    >
      {copied ? (
        <Check className="h-3.5 w-3.5 text-green-500" />
      ) : (
        <Copy className="h-3.5 w-3.5" />
      )}
    </button>
  );
}

function ApprovePanel({
  lead,
  onDone,
}: {
  lead: DemoLeadItem;
  onDone: () => void;
}) {
  const [ttlHours, setTtlHours] = useState(24);
  const [result, setResult] = useState<DemoLeadApproveResponse | null>(null);
  const queryClient = useQueryClient();

  const approveMut = useMutation({
    mutationFn: () => approveDemoLead(lead.lead_id, ttlHours),
    onSuccess: (data) => {
      setResult(data);
      queryClient.invalidateQueries({ queryKey: ["demo-leads"] });
    },
  });

  if (result) {
    return (
      <div className="rounded-lg border border-green-200 bg-green-50 p-4 text-sm">
        <p className="mb-3 font-medium text-green-800">
          Approved — email sent to {lead.email}
        </p>
        <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-gray-500">
          Tour URLs
        </p>
        {(
          [
            ["School Admin", result.demo_url_admin],
            ["Teacher", result.demo_url_teacher],
            ["Student", result.demo_url_student],
          ] as [string, string][]
        ).map(([role, url]) => (
          <div key={role} className="mb-1 flex items-center gap-1">
            <span className="w-24 text-xs text-gray-500">{role}:</span>
            <a
              href={url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 truncate text-xs text-blue-600 hover:underline"
            >
              {url.length > 60 ? url.slice(0, 60) + "…" : url}
              <ExternalLink className="h-3 w-3 shrink-0" />
            </a>
            <CopyButton text={url} />
          </div>
        ))}
        <p className="mt-2 text-xs text-gray-400">
          Expires:{" "}
          {new Date(result.token_expires_at).toLocaleString(undefined, {
            dateStyle: "medium",
            timeStyle: "short",
          })}
        </p>
        <button
          onClick={onDone}
          className="mt-3 text-xs text-gray-500 hover:underline"
        >
          Close
        </button>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 text-sm">
      <p className="mb-3 font-medium text-gray-800">
        Approve demo for{" "}
        <span className="font-bold">{lead.name}</span> ({lead.school_org})
      </p>
      <label className="mb-3 flex items-center gap-3">
        <span className="text-xs text-gray-600">Token TTL (hours)</span>
        <select
          value={ttlHours}
          onChange={(e) => setTtlHours(Number(e.target.value))}
          className="rounded border border-gray-200 px-2 py-1 text-xs"
        >
          {[12, 24, 48, 72, 168].map((h) => (
            <option key={h} value={h}>
              {h}h {h === 168 ? "(1 week)" : ""}
            </option>
          ))}
        </select>
      </label>
      <div className="flex gap-2">
        <button
          onClick={() => approveMut.mutate()}
          disabled={approveMut.isPending}
          className="rounded bg-green-600 px-4 py-1.5 text-xs font-semibold text-white hover:bg-green-700 disabled:opacity-50"
        >
          {approveMut.isPending ? "Approving…" : "Approve & send email"}
        </button>
        <button
          onClick={onDone}
          className="rounded border border-gray-200 px-4 py-1.5 text-xs text-gray-600 hover:bg-gray-50"
        >
          Cancel
        </button>
      </div>
      {approveMut.isError && (
        <p className="mt-2 text-xs text-red-600">
          Error approving lead. Try again.
        </p>
      )}
    </div>
  );
}

function RejectPanel({
  lead,
  onDone,
}: {
  lead: DemoLeadItem;
  onDone: () => void;
}) {
  const [reason, setReason] = useState("");
  const queryClient = useQueryClient();

  const rejectMut = useMutation({
    mutationFn: () => rejectDemoLead(lead.lead_id, reason || undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["demo-leads"] });
      onDone();
    },
  });

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 text-sm">
      <p className="mb-3 font-medium text-gray-800">
        Reject request from{" "}
        <span className="font-bold">{lead.name}</span>
      </p>
      <textarea
        value={reason}
        onChange={(e) => setReason(e.target.value)}
        placeholder="Reason (optional — not shown to requester)"
        rows={2}
        className="mb-3 w-full rounded border border-gray-200 px-3 py-2 text-xs focus:outline-none focus:ring-1 focus:ring-red-300"
      />
      <div className="flex gap-2">
        <button
          onClick={() => rejectMut.mutate()}
          disabled={rejectMut.isPending}
          className="rounded bg-red-600 px-4 py-1.5 text-xs font-semibold text-white hover:bg-red-700 disabled:opacity-50"
        >
          {rejectMut.isPending ? "Rejecting…" : "Reject"}
        </button>
        <button
          onClick={onDone}
          className="rounded border border-gray-200 px-4 py-1.5 text-xs text-gray-600 hover:bg-gray-50"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}

function LeadRow({ lead }: { lead: DemoLeadItem }) {
  const [expanded, setExpanded] = useState(false);
  const [action, setAction] = useState<"approve" | "reject" | null>(null);

  return (
    <div className="border-b last:border-0">
      <div className="flex items-center gap-3 px-4 py-3">
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-gray-900">
            {lead.name}
          </p>
          <p className="truncate text-xs text-gray-500">
            {lead.email} · {lead.school_org}
            {lead.ip_country && (
              <span className="ml-1 text-gray-400">({lead.ip_country})</span>
            )}
          </p>
        </div>
        <StatusBadge status={lead.status} />
        <span className="shrink-0 text-xs text-gray-400">
          {new Date(lead.created_at).toLocaleDateString()}
        </span>
        <button
          onClick={() => setExpanded((v) => !v)}
          className="text-gray-400 hover:text-gray-600"
        >
          {expanded ? (
            <ChevronUp className="h-4 w-4" />
          ) : (
            <ChevronDown className="h-4 w-4" />
          )}
        </button>
      </div>

      {expanded && (
        <div className="border-t bg-gray-50 px-4 py-3">
          {lead.status === "approved" && lead.token_expires_at && (
            <p className="mb-2 text-xs text-gray-500">
              Token expires:{" "}
              {new Date(lead.token_expires_at).toLocaleString(undefined, {
                dateStyle: "medium",
                timeStyle: "short",
              })}
            </p>
          )}
          {lead.status === "rejected" && lead.rejected_reason && (
            <p className="mb-2 text-xs text-gray-500">
              Reason: {lead.rejected_reason}
            </p>
          )}

          {lead.status === "pending" && !action && (
            <div className="flex gap-2">
              <button
                onClick={() => setAction("approve")}
                className="rounded bg-green-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-green-700"
              >
                Approve
              </button>
              <button
                onClick={() => setAction("reject")}
                className="rounded border border-red-200 px-3 py-1.5 text-xs font-semibold text-red-600 hover:bg-red-50"
              >
                Reject
              </button>
            </div>
          )}

          {action === "approve" && (
            <ApprovePanel
              lead={lead}
              onDone={() => {
                setAction(null);
                setExpanded(false);
              }}
            />
          )}
          {action === "reject" && (
            <RejectPanel
              lead={lead}
              onDone={() => {
                setAction(null);
                setExpanded(false);
              }}
            />
          )}
        </div>
      )}
    </div>
  );
}

const STATUS_TABS: { label: string; value: StatusFilter }[] = [
  { label: "All", value: "all" },
  { label: "Pending", value: "pending" },
  { label: "Approved", value: "approved" },
  { label: "Rejected", value: "rejected" },
];

export default function DemoLeadsPage() {
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("pending");

  const { data, isLoading, isError } = useQuery({
    queryKey: ["demo-leads", statusFilter],
    queryFn: () =>
      listDemoLeads(statusFilter === "all" ? undefined : statusFilter),
  });

  return (
    <div className="mx-auto max-w-4xl px-6 py-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Demo Leads</h1>
          <p className="mt-1 text-sm text-gray-500">
            Review and approve personalised tour requests.
          </p>
        </div>
        <a
          href="/admin/demo-settings"
          className="rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm text-gray-600 hover:bg-gray-50"
        >
          Geo-block settings
        </a>
      </div>

      {/* Status filter tabs */}
      <div className="mb-4 flex gap-1 rounded-lg bg-gray-100 p-1">
        {STATUS_TABS.map((tab) => (
          <button
            key={tab.value}
            onClick={() => setStatusFilter(tab.value)}
            className={`flex-1 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
              statusFilter === tab.value
                ? "bg-white text-gray-900 shadow-sm"
                : "text-gray-600 hover:text-gray-900"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Lead list */}
      <div className="overflow-hidden rounded-xl border border-gray-200 bg-white">
        {isLoading && (
          <div className="px-4 py-8 text-center text-sm text-gray-400">
            Loading…
          </div>
        )}
        {isError && (
          <div className="px-4 py-8 text-center text-sm text-red-500">
            Failed to load leads.
          </div>
        )}
        {data && data.leads.length === 0 && (
          <div className="px-4 py-8 text-center text-sm text-gray-400">
            No{" "}
            {statusFilter !== "all" ? statusFilter + " " : ""}
            leads.
          </div>
        )}
        {data &&
          data.leads.map((lead) => <LeadRow key={lead.lead_id} lead={lead} />)}
      </div>

      {data && (
        <p className="mt-3 text-right text-xs text-gray-400">
          {data.total} total
        </p>
      )}
    </div>
  );
}
