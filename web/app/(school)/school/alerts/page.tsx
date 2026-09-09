"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTeacher } from "@/lib/hooks/useTeacher";
import { getAlerts, getMyGradeScope, type AlertItem } from "@/lib/api/reports";
import { NoGradesNotice } from "@/components/school/ScopeNote";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import Link from "next/link";
import { Bell, CheckCheck, AlertTriangle, Info, Settings } from "lucide-react";
import { formatDay } from "@/lib/utils/date";

const ALERT_ICON: Record<string, React.ReactNode> = {
  // Same key mismatch as alertLabel below: the evaluator writes
  // `pass_rate_breach`, so every real alert missed this map and fell back to the
  // generic bell.
  pass_rate_breach: <AlertTriangle className="h-4 w-4 text-red-500" />,
  pass_rate_low: <AlertTriangle className="h-4 w-4 text-red-500" />,
  feedback_spike: <Info className="h-4 w-4 text-blue-500" />,
  inactive_students: <AlertTriangle className="h-4 w-4 text-orange-500" />,
  score_drop: <AlertTriangle className="h-4 w-4 text-orange-500" />,
};

function alertLabel(type: string) {
  const labels: Record<string, string> = {
    // `pass_rate_breach` is the only type the evaluator actually writes
    // (auth/tasks.py). The map listed `pass_rate_low`, which nothing emits, so
    // every real alert fell through to the raw key and the inbox showed the
    // literal string "pass_rate_breach" to teachers. Both spellings are mapped
    // rather than swapped, in case older rows carry the other one.
    pass_rate_breach: "Low pass rate",
    pass_rate_low: "Low pass rate",
    feedback_spike: "Feedback spike",
    inactive_students: "Inactive students",
    score_drop: "Score drop",
  };
  return labels[type] ?? type;
}

/** `details` is free-form JSON per alert type; read defensively. */
function unitIdOf(details: unknown): string | null {
  if (typeof details !== "object" || details === null) return null;
  const v = (details as Record<string, unknown>).unit_id;
  return typeof v === "string" ? v : null;
}

function passRateOf(details: unknown): number | null {
  if (typeof details !== "object" || details === null) return null;
  const v = (details as Record<string, unknown>).pass_rate;
  return typeof v === "number" ? Math.round(v * 10) / 10 : null;
}

export default function AlertsPage() {
  const teacher = useTeacher();
  const schoolId = teacher?.school_id ?? "";
  const qc = useQueryClient();
  // The caller's grade scope, so an empty list can be explained rather than
  // reported as "all clear" to someone who simply cannot see anything (#647).
  const { data: scope } = useQuery({
    queryKey: ["my-grade-scope", schoolId],
    queryFn: () => getMyGradeScope(schoolId),
    enabled: !!schoolId,
    staleTime: 300_000,
  });
  const hasNoScope = scope?.kind === "grades" && scope.grades.length === 0;

  const { data, isLoading } = useQuery({
    queryKey: ["alerts", schoolId],
    queryFn: () => getAlerts(schoolId),
    enabled: !!schoolId,
    staleTime: 30_000,
  });
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());

  function dismiss(alertId: string) {
    setDismissed((prev) => new Set(prev).add(alertId));
    qc.setQueryData<{ alerts: AlertItem[] }>(["alerts", schoolId], (old) => {
      if (!old) return old;
      return {
        alerts: old.alerts.map((a) =>
          a.alert_id === alertId ? { ...a, acknowledged: true } : a,
        ),
      };
    });
  }

  const visibleAlerts =
    data?.alerts?.filter((a) => !a.acknowledged && !dismissed.has(a.alert_id)) ?? [];
  const acknowledgedAlerts =
    data?.alerts?.filter((a) => a.acknowledged || dismissed.has(a.alert_id)) ?? [];

  return (
    <div className="max-w-3xl space-y-6 p-6">
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-bold text-gray-900">Alert Inbox</h1>
        {!isLoading && visibleAlerts.length > 0 && (
          <Badge className="border-red-200 bg-red-50 text-red-600">
            {visibleAlerts.length} new
          </Badge>
        )}
      </div>
      {isLoading && (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-20 rounded-lg" />
          ))}
        </div>
      )}
      {!isLoading && visibleAlerts.length > 0 && (
        <div className="space-y-3">
          {visibleAlerts.map((alert) => (
            <Card key={alert.alert_id} className="border border-orange-100 shadow-sm">
              <CardContent className="flex items-start gap-3 p-4">
                <div className="mt-0.5 shrink-0">
                  {ALERT_ICON[alert.alert_type] ?? (
                    <Bell className="h-4 w-4 text-gray-400" />
                  )}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-medium text-gray-900">
                      {alertLabel(alert.alert_type)}
                    </p>
                    {/* Which grade this alert is about (#647). The list is
                        scoped to the teacher's grades; without the grade on
                        screen a scoped list looks identical to an unscoped
                        one, and the fix is unverifiable by eye. */}
                    {alert.grade != null && (
                      <span className="rounded-full border border-gray-200 bg-gray-50 px-2 py-0.5 text-xs font-medium text-gray-600">
                        Grade {alert.grade}
                      </span>
                    )}
                    {/* "Open since", not a bare date. The evaluator re-checks
                        every morning and deliberately does NOT touch
                        `triggered_at` on a repeat breach, so this value is when
                        the breach STARTED and the alert is still live today.
                        Rendered as a plain date it reads as old news — which is
                        exactly how a tester read a still-breaching unit, and
                        why he asked why no alert had fired for it. */}
                    <span className="text-xs text-gray-400">
                      Open since {formatDay(alert.triggered_at)}
                    </span>
                  </div>
                  {/* The unit by NAME first. This used to dump every key of
                      `details`, so an alert read `unit_id: G5-TECH-004 ·
                      pass_rate: 0` — a code the teacher then could not find on
                      the Subjects page, which is exactly what was reported.
                      The id stays, demoted, because it is what appears in
                      exports and support threads. */}
                  <p className="mt-0.5 text-sm text-gray-600">
                    {alert.unit_title ?? unitIdOf(alert.details) ?? "—"}
                    {passRateOf(alert.details) != null && (
                      <span> · pass rate {passRateOf(alert.details)}%</span>
                    )}
                  </p>
                  {alert.unit_title && unitIdOf(alert.details) && (
                    <p className="mt-0.5 text-xs text-gray-400">
                      {unitIdOf(alert.details)}
                    </p>
                  )}
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  className="h-8 shrink-0"
                  onClick={() => dismiss(alert.alert_id)}
                >
                  <CheckCheck className="mr-1 h-3.5 w-3.5" />
                  Dismiss
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
      {/* A teacher with no grade assignments sees an empty list because they
          have no scope — NOT because the school is fine. "All clear" there is
          false reassurance, which is worse than showing nothing (#647). */}
      {!isLoading && visibleAlerts.length === 0 && hasNoScope ? (
        <div className="py-6">
          <NoGradesNotice scope={scope} />
        </div>
      ) : null}

      {!isLoading && visibleAlerts.length === 0 && !hasNoScope && (
        <div className="flex flex-col items-center gap-3 rounded-xl border border-gray-100 bg-gray-50 py-14 text-gray-400">
          <Bell className="h-10 w-10 opacity-50" />
          <p className="text-sm font-medium text-gray-600">
            No active alerts — all clear.
          </p>
          <p className="text-xs text-gray-400">
            Alerts fire when pass rates, inactivity, or feedback exceed your configured
            thresholds.
          </p>
          <Link
            href="/school/reports/alerts/settings"
            className="mt-1 inline-flex items-center gap-1 text-xs text-blue-600 hover:underline"
          >
            <Settings className="h-3 w-3" />
            Configure thresholds
          </Link>
        </div>
      )}
      {acknowledgedAlerts.length > 0 && (
        <div>
          <p className="mb-2 text-xs font-medium tracking-wide text-gray-400 uppercase">
            Acknowledged
          </p>
          <div className="space-y-2">
            {acknowledgedAlerts.map((alert) => (
              <div
                key={alert.alert_id}
                className="flex items-center gap-3 rounded-lg bg-gray-50 px-4 py-3 text-sm text-gray-400"
              >
                <CheckCheck className="h-4 w-4 shrink-0" />
                <span>{alertLabel(alert.alert_type)}</span>
                <span className="ml-auto text-xs">{formatDay(alert.triggered_at)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
