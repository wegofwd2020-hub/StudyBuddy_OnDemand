"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTeacher } from "@/lib/hooks/useTeacher";
import Link from "next/link";
import {
  listDefinitions,
  approveDefinition,
  rejectDefinition,
  type CurriculumDefinition,
} from "@/lib/api/school-admin";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import {
  FileText,
  Plus,
  CheckCircle2,
  XCircle,
  Clock,
  ChevronRight,
} from "lucide-react";

const STATUS_TABS = [
  { label: "Pending", value: "pending_approval" },
  { label: "Approved", value: "approved" },
  { label: "Rejected", value: "rejected" },
  { label: "All", value: "" },
];

function statusBadge(status: string) {
  if (status === "approved")
    return (
      <Badge className="border-green-200 bg-green-50 text-xs text-green-700">
        <CheckCircle2 className="mr-1 h-3 w-3" />
        Approved
      </Badge>
    );
  if (status === "rejected")
    return (
      <Badge className="border-red-200 bg-red-50 text-xs text-red-700">
        <XCircle className="mr-1 h-3 w-3" />
        Rejected
      </Badge>
    );
  return (
    <Badge className="border-amber-200 bg-amber-50 text-xs text-amber-700">
      <Clock className="mr-1 h-3 w-3" />
      Pending
    </Badge>
  );
}

// ── Definition row ─────────────────────────────────────────────────────────────

function DefinitionRow({
  defn,
  schoolId,
  isAdmin,
}: {
  defn: CurriculumDefinition;
  schoolId: string;
  isAdmin: boolean;
}) {
  const queryClient = useQueryClient();
  const [showReject, setShowReject] = useState(false);
  const [rejectReason, setRejectReason] = useState("");

  const { mutate: approve, isPending: approving } = useMutation({
    mutationFn: () => approveDefinition(schoolId, defn.definition_id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["definitions", schoolId] }),
  });

  const { mutate: reject, isPending: rejecting } = useMutation({
    mutationFn: () => rejectDefinition(schoolId, defn.definition_id, rejectReason),
    onSuccess: () => {
      setShowReject(false);
      queryClient.invalidateQueries({ queryKey: ["definitions", schoolId] });
    },
  });

  const subjectCount = defn.subjects.length;
  const unitCount = defn.subjects.reduce((acc, s) => acc + s.units.length, 0);

  return (
    <div className="rounded-lg border bg-white p-4 shadow-sm">
      <div className="flex items-start gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-medium text-gray-900">{defn.name}</span>
            <span className="rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-700">
              Grade {defn.grade}
            </span>
            {statusBadge(defn.status)}
          </div>

          <div className="mt-1 flex flex-wrap gap-3 text-xs text-gray-500">
            <span>{subjectCount} subject{subjectCount !== 1 ? "s" : ""}</span>
            <span>{unitCount} unit{unitCount !== 1 ? "s" : ""}</span>
            <span>{defn.languages.join(", ").toUpperCase()}</span>
            {defn.submitted_by_name && (
              <span>by {defn.submitted_by_name}</span>
            )}
          </div>

          {defn.status === "rejected" && defn.rejection_reason && (
            <p className="mt-2 rounded bg-red-50 px-3 py-1.5 text-xs text-red-700">
              <span className="font-medium">Reason: </span>
              {defn.rejection_reason}
            </p>
          )}

          {showReject && (
            <div className="mt-3 space-y-2">
              <Textarea
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                placeholder="Explain why this definition needs revision…"
                rows={2}
                className="text-sm"
              />
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="destructive"
                  disabled={rejecting || !rejectReason.trim()}
                  onClick={() => reject()}
                  className="h-7 text-xs"
                >
                  {rejecting ? "Rejecting…" : "Confirm rejection"}
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  className="h-7 text-xs"
                  onClick={() => setShowReject(false)}
                >
                  Cancel
                </Button>
              </div>
            </div>
          )}
        </div>

        <div className="flex shrink-0 items-center gap-1">
          {isAdmin && defn.status === "pending_approval" && !showReject && (
            <>
              <Button
                size="sm"
                className="h-7 gap-1 bg-green-600 text-xs hover:bg-green-700"
                disabled={approving}
                onClick={() => approve()}
              >
                <CheckCircle2 className="h-3 w-3" />
                {approving ? "…" : "Approve"}
              </Button>
              <Button
                size="sm"
                variant="outline"
                className="h-7 gap-1 text-xs text-red-600 border-red-200 hover:bg-red-50"
                onClick={() => setShowReject(true)}
              >
                <XCircle className="h-3 w-3" />
                Reject
              </Button>
            </>
          )}
          <Link
            href={`/school/curriculum/definitions/${defn.definition_id}`}
            className="flex items-center gap-1 rounded-md px-2 py-1 text-sm font-medium text-indigo-600 hover:bg-indigo-50"
          >
            View
            <ChevronRight className="h-4 w-4" />
          </Link>
        </div>
      </div>
    </div>
  );
}

// ── Page ───────────────────────────────────────────────────────────────────────

export default function DefinitionsPage() {
  const teacher = useTeacher();
  const schoolId = teacher?.school_id ?? "";
  const isAdmin = teacher?.role === "school_admin";
  const [tab, setTab] = useState("pending_approval");

  const { data, isLoading } = useQuery({
    queryKey: ["definitions", schoolId, tab],
    queryFn: () => listDefinitions(schoolId, tab || undefined),
    enabled: !!schoolId,
    staleTime: 30_000,
  });

  const definitions = data?.definitions ?? [];

  return (
    <div className="max-w-3xl space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FileText className="h-6 w-6 text-indigo-600" />
          <h1 className="text-2xl font-bold text-gray-900">Curriculum Definitions</h1>
        </div>
        <Link href="/school/curriculum/definitions/new">
          <Button size="sm" className="gap-2">
            <Plus className="h-4 w-4" />
            New definition
          </Button>
        </Link>
      </div>

      <p className="text-sm text-gray-500">
        A Curriculum Definition specifies the grade, subjects, and units for a custom content
        build. Submit one for school admin approval — after approval the pipeline can be
        triggered to generate the full Curriculum Package.
      </p>

      {/* Status tabs */}
      <div className="flex gap-1 rounded-lg bg-gray-100 p-1">
        {STATUS_TABS.map((t) => (
          <button
            key={t.value}
            type="button"
            onClick={() => setTab(t.value)}
            className={`flex-1 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
              tab === t.value
                ? "bg-white text-gray-900 shadow-sm"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* List */}
      {isLoading ? (
        <div className="space-y-3">
          {[1, 2].map((i) => (
            <Skeleton key={i} className="h-20 rounded-lg" />
          ))}
        </div>
      ) : definitions.length > 0 ? (
        <div className="space-y-3">
          {definitions.map((d) => (
            <DefinitionRow
              key={d.definition_id}
              defn={d}
              schoolId={schoolId}
              isAdmin={isAdmin}
            />
          ))}
        </div>
      ) : (
        <Card className="border border-dashed border-gray-200">
          <CardContent className="flex flex-col items-center gap-3 py-10 text-center">
            <FileText className="h-8 w-8 text-gray-300" />
            <p className="text-sm text-gray-400">
              {tab === "pending_approval"
                ? "No definitions awaiting approval."
                : tab === "approved"
                  ? "No approved definitions yet."
                  : tab === "rejected"
                    ? "No rejected definitions."
                    : "No definitions submitted yet."}
            </p>
            <Link href="/school/curriculum/definitions/new">
              <Button size="sm" variant="outline" className="gap-2">
                <Plus className="h-4 w-4" />
                Build your first definition
              </Button>
            </Link>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
