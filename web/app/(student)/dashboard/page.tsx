"use client";

import Image from "next/image";
import { useTranslations } from "next-intl";
import { useProgressHistory } from "@/lib/hooks/useProgress";
import { useStudentStats } from "@/lib/hooks/useStats";
import { StreakCard } from "@/components/student/StreakCard";
import { OfflineBanner } from "@/components/student/OfflineBanner";
import { LinkButton } from "@/components/ui/link-button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { BookOpen, CheckCircle2, Clock } from "lucide-react";

export default function DashboardPage() {
  const t = useTranslations("dashboard_screen");
  const { data: history, isLoading: histLoading } = useProgressHistory(5);
  const { data: stats, isLoading: statsLoading } = useStudentStats();

  return (
    <div className="flex flex-col">
      {/* Hero image */}
      <div className="relative h-[240px] w-full bg-gray-50">
        <Image
          src="/assets/books.png"
          alt="Student Portal"
          fill
          priority
          className="object-contain object-center"
        />
      </div>

      <OfflineBanner />
      <div className="max-w-4xl space-y-6 p-6">
        <h1 className="text-center text-2xl font-bold text-gray-900">{t("title")}</h1>

        {/* Streak */}
        {statsLoading ? (
          <Skeleton className="h-20 rounded-lg" />
        ) : stats ? (
          <StreakCard streakDays={stats.streak_days} sessionDates={stats.session_dates} />
        ) : null}

        {/* Quick actions */}
        <div className="grid gap-3 sm:grid-cols-3">
          <LinkButton href="/subjects" variant="outline" className="justify-start gap-2">
            <BookOpen className="h-4 w-4" /> Browse Subjects
          </LinkButton>
          <LinkButton
            href="/curriculum"
            variant="outline"
            className="justify-start gap-2"
          >
            <CheckCircle2 className="h-4 w-4" /> Curriculum Map
          </LinkButton>
          <LinkButton href="/progress" variant="outline" className="justify-start gap-2">
            <Clock className="h-4 w-4" /> View Progress
          </LinkButton>
        </div>

        {/* Recent sessions */}
        <section>
          <h2 className="mb-3 text-lg font-semibold text-gray-900">Recent Activity</h2>
          {histLoading ? (
            <div className="space-y-2">
              {[...Array(3)].map((_, i) => (
                <Skeleton key={i} className="h-16 rounded-lg" />
              ))}
            </div>
          ) : !history?.sessions.length ? (
            <p className="text-sm text-gray-400">{t("no_activity")}</p>
          ) : (
            <div className="space-y-2">
              {history.sessions.map((s) => (
                <Card key={s.session_id} className="border shadow-sm">
                  <CardContent className="flex items-center justify-between p-4">
                    <div>
                      <p className="text-sm font-medium text-gray-900">{s.unit_title}</p>
                      <p className="text-xs text-gray-400">
                        {s.subject} · {new Date(s.started_at).toLocaleDateString()}
                      </p>
                    </div>
                    {s.passed !== null && (
                      <span
                        className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                          s.passed
                            ? "bg-green-100 text-green-700"
                            : "bg-red-100 text-red-700"
                        }`}
                      >
                        {s.passed ? "Passed" : "Try again"}
                      </span>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </section>

        {/* Continue learning CTA */}
        {history?.sessions[0] && (
          <LinkButton href={`/lesson/${history.sessions[0].unit_id}`}>
            {t("continue_btn")}
          </LinkButton>
        )}
      </div>
    </div>
  );
}
