"use client";

import { useState } from "react";
import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { useTeacher } from "@/lib/hooks/useTeacher";
import { getCurriculumHealth } from "@/lib/api/reports";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
  ResponsiveContainer,
} from "recharts";

export default function UnitPerformancePage() {
  const teacher = useTeacher();
  const schoolId = teacher?.school_id ?? "";
  // null = all grades. The default, and the only value a teacher who ignores
  // the control ever sees.
  const [grade, setGrade] = useState<number | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["curriculum-health", schoolId, grade],
    queryFn: () => getCurriculumHealth(schoolId, grade),
    enabled: !!schoolId,
    staleTime: 120_000,
    // Keep the previous grade's report on screen while the next one loads.
    // Without this the chart unmounts on every change of filter and the page
    // jumps to the skeleton's height, which reads as the report breaking.
    placeholderData: keepPreviousData,
  });

  // From the server's permission scope, never from the rows on screen: deriving
  // the options from `data.units` would leave one grade selectable the moment a
  // grade was picked, with no way back to "All grades".
  const availableGrades = data?.available_grades ?? [];

  const chartData = (data?.units ?? [])
    .filter((u) => u.health_tier !== "no_activity")
    .map((u) => ({
      name: u.unit_name ?? u.unit_id.split("-").slice(-2).join("-"),
      passRate: u.first_attempt_pass_rate_pct,
      avgScore: u.avg_score_pct,
      tier: u.health_tier,
    }))
    .sort((a, b) => a.passRate - b.passRate);

  function barColor(tier: string) {
    if (tier === "struggling") return "#ef4444";
    if (tier === "watch") return "#f59e0b";
    return "#22c55e";
  }

  return (
    <div className="max-w-4xl space-y-6 p-6">
      <h1 className="text-2xl font-bold text-gray-900">Unit Performance</h1>

      {/* Grade filter. Rendered only where there is a choice to make: a school
          with one grade, or a teacher assigned to one, gets no control rather
          than a control with a single option that does nothing. */}
      {availableGrades.length > 1 && (
        <div
          role="radiogroup"
          aria-label="Filter by grade"
          className="flex flex-wrap items-center gap-2"
        >
          <span className="text-sm text-gray-500">Grade</span>
          {[null, ...availableGrades].map((g) => (
            <button
              key={g ?? "all"}
              type="button"
              role="radio"
              aria-checked={grade === g}
              onClick={() => setGrade(g)}
              className={`rounded-lg border px-3 py-1.5 text-sm transition-colors ${
                grade === g
                  ? "border-blue-500 bg-blue-50 font-medium text-blue-700"
                  : "border-gray-200 text-gray-600 hover:border-gray-300"
              }`}
            >
              {g === null ? "All grades" : `Grade ${g}`}
            </button>
          ))}
        </div>
      )}

      {isLoading && <Skeleton className="h-80 rounded-lg" />}
      {!isLoading && chartData.length > 0 && (
        <>
          <Card className="border shadow-sm">
            <CardHeader className="pb-2">
              <CardTitle className="text-base">First-attempt pass rate by unit</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer
                width="100%"
                height={Math.max(240, chartData.length * 28)}
              >
                <BarChart
                  layout="vertical"
                  data={chartData}
                  margin={{ top: 0, right: 24, bottom: 0, left: 0 }}
                >
                  <CartesianGrid
                    strokeDasharray="3 3"
                    horizontal={false}
                    stroke="#f0f0f0"
                  />
                  <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 11 }} />
                  <YAxis
                    type="category"
                    dataKey="name"
                    width={100}
                    tick={{ fontSize: 10 }}
                  />
                  <Tooltip
                    formatter={(value) => [
                      `${Number(value ?? 0).toFixed(1)}%`,
                      "Pass rate",
                    ]}
                  />
                  <Bar dataKey="passRate" name="Pass rate" radius={[0, 3, 3, 0]}>
                    {chartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={barColor(entry.tier)} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
              <div className="mt-3 flex justify-center gap-4 text-xs text-gray-500">
                <span className="flex items-center gap-1">
                  <span className="inline-block h-2.5 w-2.5 rounded-sm bg-green-500" />
                  Healthy
                </span>
                <span className="flex items-center gap-1">
                  <span className="inline-block h-2.5 w-2.5 rounded-sm bg-yellow-400" />
                  Watch
                </span>
                <span className="flex items-center gap-1">
                  <span className="inline-block h-2.5 w-2.5 rounded-sm bg-red-400" />
                  Struggling
                </span>
              </div>
            </CardContent>
          </Card>
          <Card className="border shadow-sm">
            <CardHeader className="pb-2">
              <CardTitle className="text-base">All units</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b bg-gray-50">
                      {[
                        "Unit",
                        "Subject",
                        "Pass rate",
                        "Avg score",
                        "Avg attempts",
                        "Feedback",
                      ].map((h) => (
                        <th
                          key={h}
                          className="px-4 py-2.5 text-left text-xs font-medium text-gray-500"
                        >
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {[...(data?.units ?? [])]
                      .sort(
                        (a, b) =>
                          a.first_attempt_pass_rate_pct - b.first_attempt_pass_rate_pct,
                      )
                      .map((u) => (
                        <tr key={u.unit_id} className="hover:bg-gray-50">
                          <td className="px-4 py-3 font-medium text-gray-800">
                            {u.unit_name ?? u.unit_id}
                          </td>
                          <td className="px-4 py-3 text-gray-500 capitalize">
                            {u.subject}
                          </td>
                          <td className="px-4 py-3">
                            <span
                              className={
                                u.first_attempt_pass_rate_pct >= 70
                                  ? "font-medium text-green-600"
                                  : u.first_attempt_pass_rate_pct >= 50
                                    ? "font-medium text-yellow-600"
                                    : "font-medium text-red-500"
                              }
                            >
                              {u.first_attempt_pass_rate_pct.toFixed(0)}%
                            </span>
                          </td>
                          <td className="px-4 py-3 text-gray-600">
                            {u.avg_score_pct.toFixed(0)}%
                          </td>
                          <td className="px-4 py-3 text-gray-600">
                            {u.avg_attempts_to_pass.toFixed(1)}
                          </td>
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
      {/* An empty report under a filter and an empty report overall are
          different facts, and saying "no activity recorded yet" for the first
          one blames the data for a choice the reader just made. */}
      {!isLoading && chartData.length === 0 && (
        <div className="py-12 text-center">
          <p className="text-sm text-gray-400">
            {grade === null
              ? "No unit activity recorded yet."
              : `No unit activity recorded yet for Grade ${grade}.`}
          </p>
          {grade !== null && (
            <button
              type="button"
              onClick={() => setGrade(null)}
              className="mt-2 text-sm font-medium text-blue-600 hover:underline"
            >
              Show all grades
            </button>
          )}
        </div>
      )}
    </div>
  );
}
