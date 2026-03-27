"use client";

import { useQuery } from "@tanstack/react-query";
import { useTeacher } from "@/lib/hooks/useTeacher";
import { getCurriculumHealth } from "@/lib/api/reports";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { AlertTriangle, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";

const TIER_STYLE: Record<string, string> = {
  healthy: "bg-green-50 text-green-700 border-green-200",
  watch: "bg-yellow-50 text-yellow-700 border-yellow-200",
  struggling: "bg-red-50 text-red-700 border-red-200",
  no_activity: "bg-gray-100 text-gray-500 border-gray-200",
};

export default function AtRiskReportPage() {
  const teacher = useTeacher();
  const schoolId = teacher?.school_id ?? "";

  const { data, isLoading } = useQuery({
    queryKey: ["curriculum-health", schoolId],
    queryFn: () => getCurriculumHealth(schoolId),
    enabled: !!schoolId,
    staleTime: 120_000,
  });

  const struggling = data?.units.filter((u) => u.health_tier === "struggling") ?? [];
  const watching = data?.units.filter((u) => u.health_tier === "watch") ?? [];

  return (
    <div className="p-6 max-w-4xl space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">At-Risk Report</h1>
      {isLoading && <Skeleton className="h-60 rounded-lg" />}
      {data && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[
              { label: "Healthy", count: data.healthy_count, tier: "healthy" },
              { label: "Watch", count: data.watch_count, tier: "watch" },
              { label: "Struggling", count: data.struggling_count, tier: "struggling" },
              { label: "No activity", count: data.no_activity_count, tier: "no_activity" },
            ].map(({ label, count, tier }) => (
              <Card key={tier} className="border shadow-sm">
                <CardContent className="p-4 text-center">
                  <p className="text-2xl font-bold text-gray-900">{count}</p>
                  <Badge className={cn("mt-1 text-xs", TIER_STYLE[tier])}>{label}</Badge>
                </CardContent>
              </Card>
            ))}
          </div>
          {struggling.length > 0 && (
            <Card className="border border-red-100 shadow-sm">
              <CardHeader className="pb-2">
                <CardTitle className="text-base flex items-center gap-2 text-red-700"><XCircle className="h-4 w-4" />Struggling units ({struggling.length})</CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b bg-red-50/50">
                      {["Unit","Subject","Pass rate","Avg attempts","Recommended action"].map((h) => (
                        <th key={h} className="text-left px-4 py-2.5 text-xs font-medium text-gray-500">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {struggling.map((u) => (
                      <tr key={u.unit_id} className="hover:bg-gray-50">
                        <td className="px-4 py-3 font-medium text-gray-800">{u.unit_name ?? u.unit_id}</td>
                        <td className="px-4 py-3 text-gray-500 capitalize">{u.subject}</td>
                        <td className="px-4 py-3 text-red-600 font-medium">{u.first_attempt_pass_rate_pct.toFixed(0)}%</td>
                        <td className="px-4 py-3 text-gray-600">{u.avg_attempts_to_pass.toFixed(1)}</td>
                        <td className="px-4 py-3 text-xs text-gray-500">{u.recommended_action}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </CardContent>
            </Card>
          )}
          {watching.length > 0 && (
            <Card className="border border-yellow-100 shadow-sm">
              <CardHeader className="pb-2">
                <CardTitle className="text-base flex items-center gap-2 text-yellow-700"><AlertTriangle className="h-4 w-4" />Units to watch ({watching.length})</CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b bg-yellow-50/50">
                      {["Unit","Subject","Pass rate","Avg score"].map((h) => (
                        <th key={h} className="text-left px-4 py-2.5 text-xs font-medium text-gray-500">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {watching.map((u) => (
                      <tr key={u.unit_id} className="hover:bg-gray-50">
                        <td className="px-4 py-3 font-medium text-gray-800">{u.unit_name ?? u.unit_id}</td>
                        <td className="px-4 py-3 text-gray-500 capitalize">{u.subject}</td>
                        <td className="px-4 py-3 text-yellow-600 font-medium">{u.first_attempt_pass_rate_pct.toFixed(0)}%</td>
                        <td className="px-4 py-3 text-gray-600">{u.avg_score_pct.toFixed(0)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </CardContent>
            </Card>
          )}
          {struggling.length === 0 && watching.length === 0 && <div className="text-center py-12 text-gray-400 text-sm">No at-risk units — all units are healthy.</div>}
        </>
      )}
    </div>
  );
}
