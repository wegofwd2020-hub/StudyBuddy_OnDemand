"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTeacher } from "@/lib/hooks/useTeacher";
import { getAlerts, type AlertItem } from "@/lib/api/reports";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import Link from "next/link";
import { Bell, CheckCheck, AlertTriangle, Info, Settings } from "lucide-react";

const ALERT_ICON: Record<string, React.ReactNode> = {
  pass_rate_low: <AlertTriangle className="h-4 w-4 text-red-500" />,
  feedback_spike: <Info className="h-4 w-4 text-blue-500" />,
  inactive_students: <AlertTriangle className="h-4 w-4 text-orange-500" />,
  score_drop: <AlertTriangle className="h-4 w-4 text-orange-500" />,
};

function alertLabel(type: string) {
  const labels: Record<string, string> = {
    pass_rate_low: "Low pass rate",
    feedback_spike: "Feedback spike",
    inactive_students: "Inactive students",
    score_drop: "Score drop",
  };
  return labels[type] ?? type;
}

export default function AlertsPage() {
  const teacher = useTeacher();
  const schoolId = teacher?.school_id ?? "";
  const qc = useQueryClient();
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
    data?.alerts.filter((a) => !a.acknowledged && !dismissed.has(a.alert_id)) ?? [];
  const acknowledgedAlerts =
    data?.alerts.filter((a) => a.acknowledged || dismissed.has(a.alert_id)) ?? [];

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
                    <span className="text-xs text-gray-400">
                      {new Date(alert.triggered_at).toLocaleDateString()}
                    </span>
                  </div>
                  <p className="mt-0.5 text-sm text-gray-600">
                    {typeof alert.details === "object"
                      ? Object.entries(alert.details)
                          .map(([k, v]) => `${k}: ${v}`)
                          .join(" · ")
                      : String(alert.details)}
                  </p>
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
      {!isLoading && visibleAlerts.length === 0 && (
        <div className="flex flex-col items-center gap-3 rounded-xl border border-gray-100 bg-gray-50 py-14 text-gray-400">
          <Bell className="h-10 w-10 opacity-50" />
          <p className="text-sm font-medium text-gray-600">No active alerts — all clear.</p>
          <p className="text-xs text-gray-400">
            Alerts fire when pass rates, inactivity, or feedback exceed your configured thresholds.
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
                <span className="ml-auto text-xs">
                  {new Date(alert.triggered_at).toLocaleDateString()}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
