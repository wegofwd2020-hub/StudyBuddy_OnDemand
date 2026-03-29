"use client";

import { useQuery } from "@tanstack/react-query";
import { useTeacher } from "@/lib/hooks/useTeacher";
import { getOverviewReport, getCurriculumHealth } from "@/lib/api/reports";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { TrendingDown, Users, AlertTriangle } from "lucide-react";

export default function EngagementReportPage() {
  const teacher = useTeacher();
  const schoolId = teacher?.school_id ?? "";

  const { data: overview, isLoading: loadingOv } = useQuery({
    queryKey: ["report-overview", schoolId, "30d"],
    queryFn: () => getOverviewReport(schoolId, "30d"),
    enabled: !!schoolId,
    staleTime: 120_000,
  });

  const { data: health, isLoading: loadingHealth } = useQuery({
    queryKey: ["curriculum-health", schoolId],
    queryFn: () => getCurriculumHealth(schoolId),
    enabled: !!schoolId,
    staleTime: 120_000,
  });

  const isLoading = loadingOv || loadingHealth;
  const dropoutRiskUnits =
    health?.units.filter((u) => u.health_tier === "no_activity") ?? [];

  return (
    <div className="max-w-4xl space-y-6 p-6">
      <h1 className="text-2xl font-bold text-gray-900">Engagement Report</h1>
      <p className="text-sm text-gray-500">Last 30 days</p>
      {isLoading && <Skeleton className="h-60 rounded-lg" />}
      {!isLoading && overview && (
        <>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
            <Card className="border shadow-sm">
              <CardContent className="flex items-start gap-3 p-5">
                <div className="rounded-lg bg-blue-50 p-2.5 text-blue-600">
                  <Users className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-xs font-medium tracking-wide text-gray-400 uppercase">
                    Active students
                  </p>
                  <p className="mt-0.5 text-2xl font-bold text-gray-900">
                    {overview.active_students_period}
                  </p>
                  <p className="text-xs text-gray-400">
                    of {overview.enrolled_students} enrolled
                  </p>
                </div>
              </CardContent>
            </Card>
            <Card className="border shadow-sm">
              <CardContent className="p-5">
                <p className="text-xs font-medium tracking-wide text-gray-400 uppercase">
                  Activity rate
                </p>
                <p className="mt-0.5 text-2xl font-bold text-gray-900">
                  {overview.active_pct.toFixed(0)}%
                </p>
                <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-gray-100">
                  <div
                    className="h-full rounded-full bg-blue-500"
                    style={{ width: `${Math.min(overview.active_pct, 100)}%` }}
                  />
                </div>
              </CardContent>
            </Card>
            <Card className="border shadow-sm">
              <CardContent className="p-5">
                <p className="text-xs font-medium tracking-wide text-gray-400 uppercase">
                  Audio engagement
                </p>
                <p className="mt-0.5 text-2xl font-bold text-gray-900">
                  {overview.audio_play_rate_pct.toFixed(0)}%
                </p>
                <p className="text-xs text-gray-400">of lesson views played audio</p>
              </CardContent>
            </Card>
          </div>
          {overview.active_pct < 100 && (
            <Card className="border border-orange-100 shadow-sm">
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-base text-orange-700">
                  <TrendingDown className="h-4 w-4" />
                  Inactive students
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-gray-600">
                  <span className="font-semibold text-orange-700">
                    {overview.enrolled_students - overview.active_students_period}
                  </span>{" "}
                  enrolled student
                  {overview.enrolled_students - overview.active_students_period !== 1
                    ? "s"
                    : ""}{" "}
                  had no activity in the last 30 days.
                </p>
                <p className="mt-1 text-xs text-gray-400">
                  Consider sending a nudge via the notification system.
                </p>
              </CardContent>
            </Card>
          )}
          {dropoutRiskUnits.length > 0 && (
            <Card className="border shadow-sm">
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-base text-gray-700">
                  <AlertTriangle className="h-4 w-4 text-gray-400" />
                  Units with zero activity
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="mb-3 text-xs text-gray-500">
                  These units have not been started by any student.
                </p>
                <div className="flex flex-wrap gap-2">
                  {dropoutRiskUnits.map((u) => (
                    <Badge
                      key={u.unit_id}
                      className="border-gray-200 bg-gray-100 text-xs text-gray-500"
                    >
                      {u.unit_name ?? u.unit_id} ({u.subject})
                    </Badge>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
