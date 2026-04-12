"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import { useTeacher } from "@/lib/hooks/useTeacher";
import Link from "next/link";
import {
  getDefinition,
  approveDefinition,
  rejectDefinition,
} from "@/lib/api/school-admin";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import {
  FileText,
  ChevronLeft,
  CheckCircle2,
  XCircle,
  Clock,
} from "lucide-react";

// ── Page ───────────────────────────────────────────────────────────────────────

export default function DefinitionDetailPage() {
  const params = useParams<{ definitionId: string }>();
  const definitionId = params.definitionId;
  const teacher = useTeacher();
  const router = useRouter();
  const queryClient = useQueryClient();
  const schoolId = teacher?.school_id ?? "";
  const isAdmin = teacher?.role === "school_admin";

  const [showReject, setShowReject] = useState(false);
  const [rejectReason, setRejectReason] = useState("");

  const { data: defn, isLoading } = useQuery({
    queryKey: ["definition", schoolId, definitionId],
    queryFn: () => getDefinition(schoolId, definitionId),
    enabled: !!schoolId && !!definitionId,
    staleTime: 30_000,
  });

  const { mutate: approve, isPending: approving } = useMutation({
    mutationFn: () => approveDefinition(schoolId, definitionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["definition", schoolId, definitionId] });
      queryClient.invalidateQueries({ queryKey: ["definitions", schoolId] });
    },
  });

  const { mutate: reject, isPending: rejecting } = useMutation({
    mutationFn: () => rejectDefinition(schoolId, definitionId, rejectReason),
    onSuccess: () => {
      setShowReject(false);
      queryClient.invalidateQueries({ queryKey: ["definition", schoolId, definitionId] });
      queryClient.invalidateQueries({ queryKey: ["definitions", schoolId] });
    },
  });

  if (isLoading) {
    return (
      <div className="max-w-2xl space-y-4 p-6">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-40" />
      </div>
    );
  }

  if (!defn) {
    return (
      <div className="max-w-2xl p-6">
        <p className="text-sm text-gray-500">Definition not found.</p>
        <Link href="/school/curriculum/definitions" className="mt-2 text-sm text-indigo-600 hover:underline">
          ← Back to definitions
        </Link>
      </div>
    );
  }

  const totalUnits = defn.subjects.reduce((acc, s) => acc + s.units.length, 0);

  function StatusChip() {
    if (defn!.status === "approved")
      return (
        <span className="flex items-center gap-1.5 rounded-full bg-green-50 px-3 py-1 text-sm font-medium text-green-700">
          <CheckCircle2 className="h-4 w-4" />
          Approved
        </span>
      );
    if (defn!.status === "rejected")
      return (
        <span className="flex items-center gap-1.5 rounded-full bg-red-50 px-3 py-1 text-sm font-medium text-red-700">
          <XCircle className="h-4 w-4" />
          Rejected
        </span>
      );
    return (
      <span className="flex items-center gap-1.5 rounded-full bg-amber-50 px-3 py-1 text-sm font-medium text-amber-700">
        <Clock className="h-4 w-4" />
        Pending approval
      </span>
    );
  }

  return (
    <div className="max-w-2xl space-y-6 p-6">
      {/* Back */}
      <Link
        href="/school/curriculum/definitions"
        className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-800"
      >
        <ChevronLeft className="h-4 w-4" />
        Definitions
      </Link>

      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-indigo-600" />
            <h1 className="text-xl font-bold text-gray-900">{defn.name}</h1>
          </div>
          {defn.submitted_by_name && (
            <p className="mt-0.5 text-sm text-gray-400">by {defn.submitted_by_name}</p>
          )}
        </div>
        <StatusChip />
      </div>

      {/* Summary card */}
      <Card className="border">
        <CardContent className="grid grid-cols-2 gap-4 pt-4 text-sm sm:grid-cols-4">
          <div>
            <p className="text-xs text-gray-400">Grade</p>
            <p className="font-medium text-gray-900">Grade {defn.grade}</p>
          </div>
          <div>
            <p className="text-xs text-gray-400">Languages</p>
            <p className="font-medium text-gray-900">
              {defn.languages.map((l) => l.toUpperCase()).join(", ")}
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-400">Subjects</p>
            <p className="font-medium text-gray-900">{defn.subjects.length}</p>
          </div>
          <div>
            <p className="text-xs text-gray-400">Total units</p>
            <p className="font-medium text-gray-900">{totalUnits}</p>
          </div>
        </CardContent>
      </Card>

      {/* Rejection reason */}
      {defn.status === "rejected" && defn.rejection_reason && (
        <div className="rounded-lg bg-red-50 px-4 py-3">
          <p className="text-sm font-medium text-red-800">Rejection reason</p>
          <p className="mt-1 text-sm text-red-700">{defn.rejection_reason}</p>
        </div>
      )}

      {/* Subject / unit list */}
      <div className="space-y-4">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-500">
          Subjects & units
        </h2>
        {defn.subjects.map((s, i) => (
          <Card key={i} className="border">
            <CardHeader className="pb-1">
              <CardTitle className="text-base">{s.subject_label}</CardTitle>
            </CardHeader>
            <CardContent>
              <ol className="space-y-1 pl-1">
                {s.units.map((u, j) => (
                  <li key={j} className="flex items-start gap-2 text-sm text-gray-700">
                    <span className="mt-0.5 text-xs font-mono text-gray-400">
                      {String(j + 1).padStart(2, "0")}
                    </span>
                    {u.title}
                  </li>
                ))}
              </ol>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Admin actions */}
      {isAdmin && defn.status === "pending_approval" && (
        <Card className="border border-amber-200 bg-amber-50">
          <CardHeader className="pb-2">
            <CardTitle className="text-base text-amber-900">Review this definition</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {!showReject ? (
              <div className="flex gap-3">
                <Button
                  className="gap-2 bg-green-600 hover:bg-green-700"
                  disabled={approving}
                  onClick={() => approve()}
                >
                  <CheckCircle2 className="h-4 w-4" />
                  {approving ? "Approving…" : "Approve"}
                </Button>
                <Button
                  variant="outline"
                  className="gap-2 border-red-200 text-red-600 hover:bg-red-50"
                  onClick={() => setShowReject(true)}
                >
                  <XCircle className="h-4 w-4" />
                  Reject
                </Button>
              </div>
            ) : (
              <div className="space-y-3">
                <Textarea
                  value={rejectReason}
                  onChange={(e) => setRejectReason(e.target.value)}
                  placeholder="Explain what needs to be changed…"
                  rows={3}
                />
                <div className="flex gap-2">
                  <Button
                    variant="destructive"
                    disabled={rejecting || !rejectReason.trim()}
                    onClick={() => reject()}
                  >
                    {rejecting ? "Rejecting…" : "Confirm rejection"}
                  </Button>
                  <Button variant="ghost" onClick={() => setShowReject(false)}>
                    Cancel
                  </Button>
                </div>
              </div>
            )}
            <p className="text-xs text-amber-700">
              After approval, the school admin can trigger the pipeline to generate content.
            </p>
          </CardContent>
        </Card>
      )}

      {/* Approved next step */}
      {defn.status === "approved" && (
        <div className="rounded-lg bg-green-50 px-4 py-3">
          <p className="text-sm font-medium text-green-800">Definition approved</p>
          <p className="mt-1 text-sm text-green-700">
            The pipeline can now be triggered to generate the Curriculum Package. Pipeline
            billing (Phase E) will show a cost estimate before confirming the run.
          </p>
        </div>
      )}
    </div>
  );
}
