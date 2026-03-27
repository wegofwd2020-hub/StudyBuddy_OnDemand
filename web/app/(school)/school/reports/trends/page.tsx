"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTeacher } from "@/lib/hooks/useTeacher";
import { getTrendsReport, type TrendsPeriod } from "@/lib/api/reports";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";

const PERIODS: { value: TrendsPeriod; label: string }[] = [
  { value: "4w", label: "4 weeks" },
  { value: "12w", label: "12 weeks" },
  { value: "term", label: "This term" },
];

export default function TrendsReportPage() {
  const teacher = useTeacher();
  const schoolId = teacher?.school_id ?? "";
  const [period, setPeriod] = useState<TrendsPeriod>("4w");

  const { data, isLoading } = useQuery({
    queryKey: ["report-trends", schoolId, period],
    queryFn: () => getTrendsReport(schoolId, period),
    enabled: !!schoolId,
    staleTime: 120_000,
  });

  const chartData = data?.weeks.map((w) => ({
    week: w.week_start.slice(5),
    lessons: w.lessons_viewed,
    passRate: w.first_attempt_pass_rate_pct,
    avgScore: w.avg_score_pct,
    active: w.active_students,
  })) ?? [];

  return (
    <div className="p-6 max-w-4xl space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h1 className="text-2xl font-bold text-gray-900">Trends Report</h1>
        <div className="flex gap-1 rounded-lg border p-1 bg-white">
          {PERIODS.map((p) => (
            <button key={p.value} onClick={() => setPeriod(p.value)} className={cn("px-3 py-1.5 rounded text-xs font-medium transition-colors", period === p.value ? "bg-blue-600 text-white" : "text-gray-500 hover:text-gray-900")}>{p.label}</button>
          ))}
        </div>
      </div>
      {isLoading && <Skeleton className="h-72 rounded-lg" />}
      {!isLoading && chartData.length > 0 && (
        <>
          <Card className="border shadow-sm">
            <CardHeader className="pb-2"><CardTitle className="text-base">Lesson views & active students</CardTitle></CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={240}>
                <LineChart data={chartData} margin={{ top: 4, right: 12, bottom: 0, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="week" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  <Line type="monotone" dataKey="lessons" name="Lessons viewed" stroke="#3b82f6" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="active" name="Active students" stroke="#8b5cf6" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
          <Card className="border shadow-sm">
            <CardHeader className="pb-2"><CardTitle className="text-base">Pass rate & average score (%)</CardTitle></CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={240}>
                <LineChart data={chartData} margin={{ top: 4, right: 12, bottom: 0, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="week" tick={{ fontSize: 11 }} />
                  <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} />
                  <Tooltip formatter={(value) => [`${Number(value ?? 0).toFixed(1)}%`]} />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  <Line type="monotone" dataKey="passRate" name="1st-attempt pass rate" stroke="#22c55e" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="avgScore" name="Avg score" stroke="#f59e0b" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
          <Card className="border shadow-sm">
            <CardHeader className="pb-2"><CardTitle className="text-base">Weekly breakdown</CardTitle></CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b bg-gray-50">
                      {["Week","Active","Lessons","Quizzes","Avg score","Pass rate"].map((h) => (
                        <th key={h} className="text-left px-4 py-2.5 text-xs font-medium text-gray-500">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {data!.weeks.map((w) => (
                      <tr key={w.week_start} className="hover:bg-gray-50">
                        <td className="px-4 py-2.5 text-gray-600">{w.week_start}</td>
                        <td className="px-4 py-2.5">{w.active_students}</td>
                        <td className="px-4 py-2.5">{w.lessons_viewed}</td>
                        <td className="px-4 py-2.5">{w.quiz_attempts}</td>
                        <td className="px-4 py-2.5">{w.avg_score_pct.toFixed(1)}%</td>
                        <td className="px-4 py-2.5">{w.first_attempt_pass_rate_pct.toFixed(1)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </>
      )}
      {!isLoading && chartData.length === 0 && <p className="text-sm text-gray-400 text-center py-12">No trend data for this period.</p>}
    </div>
  );
}
