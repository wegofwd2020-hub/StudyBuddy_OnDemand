"use client";

import { useState } from "react";
import { useStudentStats } from "@/lib/hooks/useStats";
import { OfflineBanner } from "@/components/student/OfflineBanner";
import { StatCard } from "@/components/student/StatCard";
import { StreakCard } from "@/components/student/StreakCard";
import { Skeleton } from "@/components/ui/skeleton";
import { useTranslations } from "next-intl";
import {
  BookOpen, CheckCircle2, TrendingUp, Star, Volume2, BarChart3
} from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
} from "recharts";

type Period = "7d" | "30d" | "all";

const PERIODS: { label: string; value: Period }[] = [
  { label: "Last 7 days", value: "7d" },
  { label: "Last 30 days", value: "30d" },
  { label: "All time", value: "all" },
];

export default function StatsPage() {
  const t = useTranslations("stats_screen");
  const [period, setPeriod] = useState<Period>("30d");
  const { data: stats, isLoading } = useStudentStats(period);

  return (
    <div className="flex flex-col">
      <OfflineBanner />
      <div className="p-6 max-w-4xl space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-900">{t("title")}</h1>
          {/* Period selector */}
          <div className="flex gap-1 rounded-lg border p-1 bg-white">
            {PERIODS.map((p) => (
              <button
                key={p.value}
                onClick={() => setPeriod(p.value)}
                className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
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
        ) : !stats ? null : (
          <>
            {/* Streak */}
            <StreakCard streakDays={stats.streak_days} sessionDates={stats.session_dates} />

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
            {stats.subject_breakdown.length > 0 && (
              <section>
                <h2 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
                  <BarChart3 className="h-4 w-4" />
                  Subject Breakdown
                </h2>
                <div className="rounded-lg border bg-white p-4 shadow-sm">
                  <ResponsiveContainer width="100%" height={200}>
                    <BarChart data={stats.subject_breakdown} margin={{ top: 0, right: 0, bottom: 0, left: -20 }}>
                      <XAxis dataKey="subject" tick={{ fontSize: 11 }} />
                      <YAxis tick={{ fontSize: 11 }} />
                      <Tooltip
                        formatter={(value) => [Number(value ?? 0), "Lessons"]}
                        labelStyle={{ fontSize: 12 }}
                      />
                      <Bar dataKey="lessons" radius={[4, 4, 0, 0]}>
                        {stats.subject_breakdown.map((_, i) => (
                          <Cell
                            key={i}
                            fill={["#3b82f6", "#8b5cf6", "#10b981", "#f59e0b", "#ef4444"][i % 5]}
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
