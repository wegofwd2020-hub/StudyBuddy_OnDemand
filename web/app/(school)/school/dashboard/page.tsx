"use client";

import { useQuery } from "@tanstack/react-query";
import { useTeacher } from "@/lib/hooks/useTeacher";
import { getOverviewReport, getAlerts } from "@/lib/api/reports";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { LinkButton } from "@/components/ui/link-button";
import { Badge } from "@/components/ui/badge";
import { Users, BookOpen, CheckCircle, Bell, TrendingUp, AlertTriangle } from "lucide-react";

function KpiCard({
  title, value, subtitle, icon, accent,
}: {
  title: string; value: string | number; subtitle?: string;
  icon: React.ReactNode; accent?: "green" | "blue" | "red" | "gray";
}) {
  const colors = {
    green: "text-green-600 bg-green-50",
    blue: "text-blue-600 bg-blue-50",
    red: "text-red-500 bg-red-50",
    gray: "text-gray-500 bg-gray-100",
  };
  return (
    <Card className="border shadow-sm">
      <CardContent className="p-5 flex items-start gap-4">
        <div className={`rounded-lg p-2.5 ${colors[accent ?? "blue"]}`}>{icon}</div>
        <div>
          <p className="text-xs text-gray-400 font-medium uppercase tracking-wide">{title}</p>
          <p className="text-2xl font-bold text-gray-900 mt-0.5">{value}</p>
          {subtitle && <p className="text-xs text-gray-500 mt-0.5">{subtitle}</p>}
        </div>
      </CardContent>
    </Card>
  );
}

export default function SchoolDashboard() {
  const teacher = useTeacher();
  const schoolId = teacher?.school_id ?? "";

  const { data: overview, isLoading } = useQuery({
    queryKey: ["report-overview", schoolId, "7d"],
    queryFn: () => getOverviewReport(schoolId, "7d"),
    enabled: !!schoolId,
    staleTime: 120_000,
  });

  const { data: alertsData } = useQuery({
    queryKey: ["alerts", schoolId],
    queryFn: () => getAlerts(schoolId),
    enabled: !!schoolId,
    staleTime: 60_000,
  });

  const unreadAlerts = alertsData?.alerts.filter((a) => !a.acknowledged).length ?? 0;

  return (
    <div className="p-6 space-y-8 max-w-5xl">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Teacher Dashboard</h1>
        <div className="flex gap-2">
          {unreadAlerts > 0 && (
            <LinkButton href="/school/alerts" variant="outline" size="sm">
              <Bell className="h-4 w-4 mr-1.5 text-red-500" />
              {unreadAlerts} alert{unreadAlerts !== 1 ? "s" : ""}
            </LinkButton>
          )}
          <LinkButton href="/school/reports/overview" size="sm">View full report</LinkButton>
        </div>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-28 rounded-lg" />)}
        </div>
      ) : overview ? (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <KpiCard title="Enrolled students" value={overview.enrolled_students} icon={<Users className="h-5 w-5" />} accent="blue" />
          <KpiCard title="Active this week" value={`${overview.active_pct.toFixed(0)}%`} subtitle={`${overview.active_students_period} of ${overview.enrolled_students}`} icon={<TrendingUp className="h-5 w-5" />} accent="green" />
          <KpiCard title="Lessons viewed" value={overview.lessons_viewed} subtitle="Last 7 days" icon={<BookOpen className="h-5 w-5" />} accent="blue" />
          <KpiCard title="Pass rate (1st attempt)" value={`${overview.first_attempt_pass_rate_pct.toFixed(0)}%`} icon={<CheckCircle className="h-5 w-5" />} accent={overview.first_attempt_pass_rate_pct >= 60 ? "green" : "red"} />
          <KpiCard title="Quiz attempts" value={overview.quiz_attempts} icon={<BookOpen className="h-5 w-5" />} accent="gray" />
          <KpiCard title="Unreviewed feedback" value={overview.unreviewed_feedback_count} icon={<Bell className="h-5 w-5" />} accent={overview.unreviewed_feedback_count > 0 ? "red" : "gray"} />
        </div>
      ) : null}

      {overview && overview.units_with_struggles.length > 0 && (
        <Card className="border shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-base flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-orange-500" />
              Units needing attention
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {overview.units_with_struggles.map((uid) => (
                <Badge key={uid} className="bg-orange-50 text-orange-700 border-orange-200">{uid}</Badge>
              ))}
            </div>
            <LinkButton href="/school/reports/at-risk" variant="outline" size="sm" className="mt-3">
              View at-risk report
            </LinkButton>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        {[
          { label: "Class overview", href: "/school/class/all" },
          { label: "Trends report", href: "/school/reports/trends" },
          { label: "Unit performance", href: "/school/reports/units" },
          { label: "Student feedback", href: "/school/reports/feedback" },
          { label: "Export CSV", href: "/school/reports/export" },
          { label: "Alert inbox", href: "/school/alerts" },
        ].map((link) => (
          <LinkButton key={link.href} href={link.href} variant="outline" className="justify-start">
            {link.label}
          </LinkButton>
        ))}
      </div>
    </div>
  );
}
