"use client";

import { useState } from "react";
import { useStudentStats } from "@/lib/hooks/useStats";
import { OfflineBanner } from "@/components/student/OfflineBanner";
import { StatCard } from "@/components/student/StatCard";
import { StreakCard } from "@/components/student/StreakCard";
import { Skeleton } from "@/components/ui/skeleton";
import { useTranslations } from "next-intl";
import {
  BookOpen,
  CheckCircle2,
  TrendingUp,
  Star,
  Volume2,
  BarChart3,
  BarChart2,
} from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";

type Period = "7d" | "30d" | "all";

const PERIODS: { label: string; value: Period }[] = [
  { label: "Last 7 days", value: "7d" },
  { label: "Last 30 days", value: "30d" },
  { label: "All time", value: "all" },
];

// Note: this vocabulary ("7d"/"30d"/"all") is intentionally not the same set
// as the school-admin dashboard's period selector ("7d"/"30d"/"term") — the
// admin overview endpoint has no "all time" concept and this per-student
// endpoint has no school "term" concept. The "7d"/"30d" values that ARE
// shared mean the same window on both screens.

export default function StatsPage() {
  const t = useTranslations("stats_screen");
  const [period, setPeriod] = useState<Period>("30d");
  const { data: stats, isLoading } = useStudentStats(period);

  return (
    <div className="flex flex-col">
      <OfflineBanner />
      <div className="max-w-4xl space-y-6 p-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{t("title")}</h1>
            {/* Explicit window label so the active period is legible without
                relying on the reader to notice which pill is highlighted. */}
            <p className="mt-0.5 text-xs text-gray-400">
              Showing {PERIODS.find((p) => p.value === period)?.label.toLowerCase()}
            </p>
          </div>
          {/* Period selector */}
          <div className="flex gap-1 rounded-lg border bg-white p-1">
            {PERIODS.map((p) => (
              <button
                key={p.value}
                onClick={() => setPeriod(p.value)}
                className={`rounded px-3 py-1 text-xs font-medium transition-colors ${
                  period === p.value
                    ? "bg-blue-600 text-white"
                    : "text-gray-500 hover:text-gray-900"
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>

        {isLoading ? (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {[...Array(6)].map((_, i) => (
              <Skeleton key={i} className="h-20 rounded-lg" />
            ))}
          </div>
        ) : !stats || stats.quizzes_completed === 0 ? (
          <div className="rounded-xl border border-gray-200 bg-white py-16 text-center">
            <BarChart2 className="mx-auto mb-3 h-10 w-10 text-gray-300" />
            <p className="mb-1 text-sm font-medium text-gray-600">No stats yet</p>
            <p className="mb-4 text-xs text-gray-400">
              Complete your first quiz to start tracking your progress here.
            </p>
            <a
              href="/subjects"
              className="inline-flex items-center gap-1 rounded-lg bg-indigo-600 px-4 py-2 text-xs font-medium text-white hover:bg-indigo-700"
            >
              <BookOpen className="h-3.5 w-3.5" />
              Browse Subjects
            </a>
          </div>
        ) : (
          <>
            {/* Streak */}
            <StreakCard
              streakDays={stats.streak_days}
              sessionDates={stats.session_dates}
            />

            {/* KPI grid */}
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              <StatCard
                label={t("lessons_viewed")}
                value={stats.lessons_viewed}
                icon={BookOpen}
                color="blue"
              />
              <StatCard
                label={t("quizzes_completed")}
                value={stats.quizzes_completed}
                icon={CheckCircle2}
                color="green"
              />
              <StatCard
                label={t("pass_rate")}
                value={`${Math.round(stats.pass_rate * 100)}%`}
                icon={TrendingUp}
                color="purple"
              />
              <StatCard
                label={t("avg_score")}
                value={`${Math.round(stats.avg_score * 100)}%`}
                icon={Star}
                color="orange"
              />
              <StatCard
                label={t("audio_played")}
                value={stats.audio_sessions}
                icon={Volume2}
                color="blue"
              />
            </div>

            {/* Subject breakdown chart */}
            {stats.subject_breakdown && stats.subject_breakdown.length > 0 && (
              <section>
                <h2 className="mb-1 flex items-center gap-2 text-lg font-semibold text-gray-800">
                  <BarChart3 className="h-4 w-4" />
                  Subject Breakdown
                </h2>
                {/* State the unit of measure so the chart isn't misread as the
                    "lessons viewed" tile — it counts quiz attempts (#525). */}
                <p className="mb-4 text-sm text-gray-500">Quiz attempts per subject</p>
                <div className="rounded-lg border bg-white p-4 shadow-sm">
                  <ResponsiveContainer width="100%" height={200}>
                    <BarChart
                      data={stats.subject_breakdown}
                      margin={{ top: 0, right: 0, bottom: 0, left: -20 }}
                    >
                      <XAxis dataKey="subject" tick={{ fontSize: 11 }} />
                      <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                      <Tooltip
                        formatter={(value) => [Number(value ?? 0), "Quiz attempts"]}
                        labelStyle={{ fontSize: 12 }}
                      />
                      {/* Cap width so a single subject renders as a normal bar
                          rather than one block spanning the whole chart (#473). */}
                      <Bar dataKey="attempts" radius={[4, 4, 0, 0]} maxBarSize={64}>
                        {stats.subject_breakdown.map((_, i) => (
                          <Cell
                            key={i}
                            fill={
                              ["#3b82f6", "#8b5cf6", "#10b981", "#f59e0b", "#ef4444"][
                                i % 5
                              ]
                            }
                          />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </section>
            )}
          </>
        )}
      </div>
    </div>
  );
}
