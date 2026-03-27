"use client";

import { useQuery } from "@tanstack/react-query";
import { useTeacher } from "@/lib/hooks/useTeacher";
import { getCurriculumHealth } from "@/lib/api/reports";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell, ResponsiveContainer } from "recharts";

export default function UnitPerformancePage() {
  const teacher = useTeacher();
  const schoolId = teacher?.school_id ?? "";

  const { data, isLoading } = useQuery({
    queryKey: ["curriculum-health", schoolId],
    queryFn: () => getCurriculumHealth(schoolId),
    enabled: !!schoolId,
    staleTime: 120_000,
  });

  const chartData = (data?.units ?? [])
    .filter((u) => u.health_tier !== "no_activity")
    .map((u) => ({ name: u.unit_name ?? u.unit_id.split("-").slice(-2).join("-"), passRate: u.first_attempt_pass_rate_pct, avgScore: u.avg_score_pct, tier: u.health_tier }))
    .sort((a, b) => a.passRate - b.passRate);

  function barColor(tier: string) {
    if (tier === "struggling") return "#ef4444";
    if (tier === "watch") return "#f59e0b";
    return "#22c55e";
  }

  return (
    <div className="p-6 max-w-4xl space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Unit Performance</h1>
      {isLoading && <Skeleton className="h-80 rounded-lg" />}
      {!isLoading && chartData.length > 0 && (
        <>
          <Card className="border shadow-sm">
            <CardHeader className="pb-2"><CardTitle className="text-base">First-attempt pass rate by unit</CardTitle></CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={Math.max(240, chartData.length * 28)}>
                <BarChart layout="vertical" data={chartData} margin={{ top: 0, right: 24, bottom: 0, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f0f0f0" />
                  <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 11 }} />
                  <YAxis type="category" dataKey="name" width={100} tick={{ fontSize: 10 }} />
                  <Tooltip formatter={(value) => [`${Number(value ?? 0).toFixed(1)}%`, "Pass rate"]} />
                  <Bar dataKey="passRate" name="Pass rate" radius={[0, 3, 3, 0]}>
                    {chartData.map((entry, index) => <Cell key={`cell-${index}`} fill={barColor(entry.tier)} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
              <div className="flex gap-4 mt-3 justify-center text-xs text-gray-500">
                <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-sm bg-green-500 inline-block" />Healthy</span>
                <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-sm bg-yellow-400 inline-block" />Watch</span>
                <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-sm bg-red-400 inline-block" />Struggling</span>
              </div>
            </CardContent>
          </Card>
          <Card className="border shadow-sm">
            <CardHeader className="pb-2"><CardTitle className="text-base">All units</CardTitle></CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b bg-gray-50">
                      {["Unit","Subject","Pass rate","Avg score","Avg attempts","Feedback"].map((h) => (
                        <th key={h} className="text-left px-4 py-2.5 text-xs font-medium text-gray-500">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {[...(data?.units ?? [])].sort((a, b) => a.first_attempt_pass_rate_pct - b.first_attempt_pass_rate_pct).map((u) => (
                      <tr key={u.unit_id} className="hover:bg-gray-50">
                        <td className="px-4 py-3 font-medium text-gray-800">{u.unit_name ?? u.unit_id}</td>
                        <td className="px-4 py-3 text-gray-500 capitalize">{u.subject}</td>
                        <td className="px-4 py-3"><span className={u.first_attempt_pass_rate_pct >= 70 ? "text-green-600 font-medium" : u.first_attempt_pass_rate_pct >= 50 ? "text-yellow-600 font-medium" : "text-red-500 font-medium"}>{u.first_attempt_pass_rate_pct.toFixed(0)}%</span></td>
                        <td className="px-4 py-3 text-gray-600">{u.avg_score_pct.toFixed(0)}%</td>
                        <td className="px-4 py-3 text-gray-600">{u.avg_attempts_to_pass.toFixed(1)}</td>
                        <td className="px-4 py-3 text-gray-500">{u.feedback_count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </>
      )}
      {!isLoading && chartData.length === 0 && <p className="text-center text-sm text-gray-400 py-12">No unit activity recorded yet.</p>}
    </div>
  );
}
