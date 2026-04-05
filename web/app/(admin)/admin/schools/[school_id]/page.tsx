"use client";

import { useParams } from "next/navigation";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getAdminSchoolLimits,
  setAdminSchoolLimits,
  clearAdminSchoolLimits,
} from "@/lib/api/admin";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { LinkButton } from "@/components/ui/link-button";
import { Loader2, AlertTriangle, CheckCircle, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";

// ── Limits display ────────────────────────────────────────────────────────────

function LimitRow({
  label,
  effective,
  override,
  planDefault,
}: {
  label: string;
  effective: number;
  override: number | null | undefined;
  planDefault: number;
}) {
  const isOverridden = override != null;
  return (
    <div className="flex items-center justify-between border-b py-2.5 last:border-0">
      <span className="text-sm text-gray-600">{label}</span>
      <div className="flex items-center gap-3 text-right">
        {isOverridden && (
          <span className="text-xs text-gray-400 line-through">{planDefault}</span>
        )}
        <span
          className={cn(
            "text-sm font-semibold",
            isOverridden ? "text-amber-600" : "text-gray-800",
          )}
        >
          {effective}
          {isOverridden && (
            <span className="ml-1 text-xs font-normal text-amber-500">(override)</span>
          )}
        </span>
      </div>
    </div>
  );
}

// ── Override form ─────────────────────────────────────────────────────────────

function OverrideForm({
  schoolId,
  existing,
  planDefaults,
  onSaved,
}: {
  schoolId: string;
  existing: { max_students: number | null; max_teachers: number | null; pipeline_quota: number | null; override_reason: string } | null;
  planDefaults: { max_students: number; max_teachers: number; pipeline_quota: number };
  onSaved: () => void;
}) {
  const [maxStudents, setMaxStudents] = useState<string>(
    existing?.max_students?.toString() ?? "",
  );
  const [maxTeachers, setMaxTeachers] = useState<string>(
    existing?.max_teachers?.toString() ?? "",
  );
  const [pipelineQuota, setPipelineQuota] = useState<string>(
    existing?.pipeline_quota?.toString() ?? "",
  );
  const [reason, setReason] = useState(existing?.override_reason ?? "");
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () =>
      setAdminSchoolLimits(schoolId, {
        max_students: maxStudents ? parseInt(maxStudents) : null,
        max_teachers: maxTeachers ? parseInt(maxTeachers) : null,
        pipeline_quota: pipelineQuota ? parseInt(pipelineQuota) : null,
        override_reason: reason,
      }),
    onSuccess: () => {
      setSaved(true);
      setError(null);
      setTimeout(() => setSaved(false), 3000);
      onSaved();
    },
    onError: (err: unknown) => {
      const msg =
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
          : "Failed to save override.";
      setError(msg);
    },
  });

  const canSave = reason.trim().length > 0 && !mutation.isPending;

  return (
    <div className="space-y-4">
      <p className="text-xs text-gray-500">
        Leave a field blank to fall back to the plan default. All fields are optional
        except the reason.
      </p>

      <div className="grid grid-cols-3 gap-4">
        <div className="space-y-1.5">
          <Label htmlFor="ov_students">
            Max students
            <span className="ml-1.5 text-gray-400">(plan: {planDefaults.max_students})</span>
          </Label>
          <Input
            id="ov_students"
            type="number"
            min={1}
            value={maxStudents}
            onChange={(e) => setMaxStudents(e.target.value)}
            placeholder={String(planDefaults.max_students)}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="ov_teachers">
            Max teachers
            <span className="ml-1.5 text-gray-400">(plan: {planDefaults.max_teachers})</span>
          </Label>
          <Input
            id="ov_teachers"
            type="number"
            min={1}
            value={maxTeachers}
            onChange={(e) => setMaxTeachers(e.target.value)}
            placeholder={String(planDefaults.max_teachers)}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="ov_pipeline">
            Pipeline quota / mo
            <span className="ml-1.5 text-gray-400">(plan: {planDefaults.pipeline_quota})</span>
          </Label>
          <Input
            id="ov_pipeline"
            type="number"
            min={0}
            value={pipelineQuota}
            onChange={(e) => setPipelineQuota(e.target.value)}
            placeholder={String(planDefaults.pipeline_quota)}
          />
        </div>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="ov_reason">
          Reason <span className="text-red-500">*</span>
        </Label>
        <Input
          id="ov_reason"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="e.g. VIP school, special arrangement with sales"
        />
      </div>

      {error && (
        <p className="text-xs text-red-600">{error}</p>
      )}

      <div className="flex items-center gap-3">
        <Button onClick={() => mutation.mutate()} disabled={!canSave} className="gap-2">
          {mutation.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : null}
          {existing ? "Update override" : "Set override"}
        </Button>
        {saved && (
          <span className="flex items-center gap-1 text-xs text-green-600">
            <CheckCircle className="h-3.5 w-3.5" />
            Saved
          </span>
        )}
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function AdminSchoolDetailPage() {
  const { school_id } = useParams<{ school_id: string }>();
  const queryClient = useQueryClient();
  const [clearError, setClearError] = useState<string | null>(null);
  const [clearSuccess, setClearSuccess] = useState(false);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["admin-school-limits", school_id],
    queryFn: () => getAdminSchoolLimits(school_id),
    enabled: !!school_id,
    staleTime: 30_000,
  });

  const clearMutation = useMutation({
    mutationFn: () => clearAdminSchoolLimits(school_id),
    onSuccess: () => {
      setClearSuccess(true);
      setClearError(null);
      setTimeout(() => setClearSuccess(false), 3000);
      void queryClient.invalidateQueries({ queryKey: ["admin-school-limits", school_id] });
      void queryClient.invalidateQueries({ queryKey: ["admin-schools"] });
    },
    onError: (err: unknown) => {
      const msg =
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
          : "Failed to clear override.";
      setClearError(msg);
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="p-6">
        <p className="text-sm text-gray-500">School not found.</p>
        <LinkButton href="/admin/schools" variant="outline" className="mt-4">
          ← Back to schools
        </LinkButton>
      </div>
    );
  }

  // Derive plan defaults from effective limits and override (reverse-engineer for display)
  const planDefaults = {
    max_students: data.override?.max_students != null
      ? data.max_students  // overridden, so effective = override
      : data.max_students, // not overridden, effective = plan default
    max_teachers: data.override?.max_teachers != null
      ? data.max_teachers
      : data.max_teachers,
    pipeline_quota: data.override?.pipeline_quota != null
      ? data.pipeline_quota_monthly
      : data.pipeline_quota_monthly,
  };
  // If override exists, plan default is the effective value only when that field is NOT overridden.
  // Since we don't store plan defaults separately in the response, show them as-is for non-overridden fields.

  const resetDate = new Date(data.pipeline_resets_at).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });

  return (
    <div className="max-w-3xl space-y-6 p-6">
      <div className="flex items-center gap-3">
        <LinkButton href="/admin/schools" variant="outline" size="sm">
          ← Schools
        </LinkButton>
        <div>
          <h1 className="text-xl font-bold text-gray-900">School Limits &amp; Override</h1>
          <p className="mt-0.5 font-mono text-xs text-gray-400">{school_id}</p>
        </div>
      </div>

      {/* Effective limits */}
      <Card className="border shadow-sm">
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-base">
            Effective limits
            <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium capitalize text-gray-600">
              {data.plan}
            </span>
            {data.has_override && (
              <span className="flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-700">
                <AlertTriangle className="h-3 w-3" />
                Override active
              </span>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <LimitRow
            label="Max students"
            effective={data.max_students}
            override={data.override?.max_students}
            planDefault={data.max_students}
          />
          <LimitRow
            label="Max teachers"
            effective={data.max_teachers}
            override={data.override?.max_teachers}
            planDefault={data.max_teachers}
          />
          <LimitRow
            label="Pipeline quota / month"
            effective={data.pipeline_quota_monthly}
            override={data.override?.pipeline_quota}
            planDefault={data.pipeline_quota_monthly}
          />
          <div className="mt-3 flex gap-6 text-xs text-gray-500">
            <span>
              Pipeline used this month:{" "}
              <strong className="text-gray-700">{data.pipeline_runs_this_month}</strong> /{" "}
              {data.pipeline_quota_monthly} — resets {resetDate}
            </span>
            <span>
              Seats used:{" "}
              <strong className="text-gray-700">{data.seats_used_students}</strong> students,{" "}
              <strong className="text-gray-700">{data.seats_used_teachers}</strong> teachers
            </span>
          </div>
        </CardContent>
      </Card>

      {/* Current override detail */}
      {data.has_override && data.override && (
        <Card className="border border-amber-200 shadow-sm bg-amber-50/40">
          <CardHeader className="pb-2">
            <CardTitle className="text-base text-amber-800">Current override</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <dl className="grid grid-cols-2 gap-x-6 gap-y-2">
              <div>
                <dt className="text-xs text-gray-400">Reason</dt>
                <dd className="text-gray-800">{data.override.override_reason}</dd>
              </div>
              <div>
                <dt className="text-xs text-gray-400">Set at</dt>
                <dd className="text-gray-700">
                  {new Date(data.override.set_at).toLocaleString(undefined, {
                    month: "short",
                    day: "numeric",
                    year: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </dd>
              </div>
              <div>
                <dt className="text-xs text-gray-400">Overridden fields</dt>
                <dd className="text-gray-700">
                  {[
                    data.override.max_students != null && `students → ${data.override.max_students}`,
                    data.override.max_teachers != null && `teachers → ${data.override.max_teachers}`,
                    data.override.pipeline_quota != null && `pipeline → ${data.override.pipeline_quota}`,
                  ]
                    .filter(Boolean)
                    .join(", ") || "none"}
                </dd>
              </div>
            </dl>

            <div className="flex items-center gap-3 pt-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => clearMutation.mutate()}
                disabled={clearMutation.isPending}
                className="gap-2 border-red-200 text-red-600 hover:bg-red-50"
              >
                {clearMutation.isPending ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Trash2 className="h-3.5 w-3.5" />
                )}
                Clear override
              </Button>
              {clearSuccess && (
                <span className="flex items-center gap-1 text-xs text-green-600">
                  <CheckCircle className="h-3.5 w-3.5" />
                  Override cleared
                </span>
              )}
              {clearError && (
                <span className="text-xs text-red-600">{clearError}</span>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Set / update override */}
      <Card className="border shadow-sm">
        <CardHeader className="pb-2">
          <CardTitle className="text-base">
            {data.has_override ? "Update override" : "Set override"}
          </CardTitle>
          <p className="text-sm text-gray-500">
            Override specific limits for this school. NULL fields fall back to the plan
            default. Changes are attributed to your admin account in the audit log.
          </p>
        </CardHeader>
        <CardContent>
          <OverrideForm
            schoolId={school_id}
            existing={data.override ?? null}
            planDefaults={planDefaults}
            onSaved={() => {
              void refetch();
              void queryClient.invalidateQueries({ queryKey: ["admin-schools"] });
            }}
          />
        </CardContent>
      </Card>
    </div>
  );
}
