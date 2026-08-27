"use client";

import { useTranslations } from "next-intl";
import { ArrowRight, BookOpen, CheckCircle2, Clock, Sparkles } from "lucide-react";

import { useStudentDashboard } from "@/lib/hooks/useStudentDashboard";
import { useStudentStats } from "@/lib/hooks/useStats";
import { StreakCard } from "@/components/student/StreakCard";
import { OfflineBanner } from "@/components/student/OfflineBanner";
import { LinkButton } from "@/components/ui/link-button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

/**
 * Student dashboard (#640, design §11).
 *
 * The product owner's four questions in Venki's proposed shell. His layout was
 * never the problem — the tiles inside it were a teacher's, and a student
 * opening their own dashboard to "units with struggles" is being shown a list
 * of their failures on the first screen they see.
 *
 *   1. What am I doing next        -> the right-hand panel
 *   2. What needs completing       -> WAITS on the academic calendar (ADR-007);
 *                                     there is nothing to count down to yet
 *   3. My subjects and scores      -> the wide card
 *   4. My standing in the class    -> a tile, when the cohort allows it
 *
 * Dropped from the wireframe, each for a reason: audio play rate (0 plays across
 * 86 lesson views, ever — a permanently-0% tile), units with no activity (#590),
 * units with struggles (above), and first-attempt pass rate, which is a
 * management metric — a student gets their average score instead, which answers
 * question 3 and reads as progress rather than judgement.
 *
 * No period selector, deliberately. Every figure here is cumulative — units
 * done out of a curriculum, an average over all attempts, a standing against
 * the cohort's own cumulative average. A selector that silently filtered none
 * of them would be the "Quizzes completed shows 6" defect again, in a new place.
 * It arrives with question 2, which is the first thing on this page that has a
 * period at all.
 */
export default function DashboardPage() {
  const t = useTranslations("dashboard_screen");
  const { data, isLoading } = useStudentDashboard();
  const { data: stats, isLoading: statsLoading } = useStudentStats();

  return (
    <div className="flex flex-col">
      <OfflineBanner />

      <div className="mx-auto w-full max-w-6xl space-y-6 p-6">
        <header>
          <h1 className="text-2xl font-bold text-gray-900">{t("title")}</h1>
          <p className="mt-1 text-sm text-gray-500">
            Where you are across your subjects, and what to pick up next.
          </p>
        </header>

        {/* ── Tiles ────────────────────────────────────────────────────── */}
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {statsLoading ? (
            <Skeleton className="h-24 rounded-lg" />
          ) : stats ? (
            <StreakCard
              streakDays={stats.streak_days}
              sessionDates={stats.session_dates}
            />
          ) : null}

          {isLoading ? (
            <>
              <Skeleton className="h-24 rounded-lg" />
              <Skeleton className="h-24 rounded-lg" />
            </>
          ) : (
            <>
              <Card>
                <CardContent className="p-4">
                  <p className="text-xs font-medium tracking-wide text-gray-500 uppercase">
                    Units done
                  </p>
                  <p className="mt-1 text-2xl font-bold text-gray-900">
                    {data?.summary.units_completed ?? 0}
                    <span className="ml-1 text-base font-normal text-gray-400">
                      / {totalUnits(data)}
                    </span>
                  </p>
                  <p className="mt-1 text-xs text-gray-400">across your curriculum</p>
                </CardContent>
              </Card>

              {/* Only rendered when a cohort is large enough to aggregate
                  without disclosing one classmate's record. Absent, not empty:
                  a tile explaining why it cannot compare you is worse than no
                  tile. */}
              {data?.standing ? (
                <Card>
                  <CardContent className="p-4">
                    <p className="text-xs font-medium tracking-wide text-gray-500 uppercase">
                      You vs your grade
                    </p>
                    <p className="mt-1 text-2xl font-bold text-gray-900">
                      {data.standing.you}%
                      <span className="ml-2 text-base font-normal text-gray-400">
                        class {data.standing.cohort}%
                      </span>
                    </p>
                    <p className="mt-1 text-xs text-gray-400">
                      average across Grade {data.standing.grade} (
                      {data.standing.cohort_size} students)
                    </p>
                  </CardContent>
                </Card>
              ) : (
                <Card>
                  <CardContent className="p-4">
                    <p className="text-xs font-medium tracking-wide text-gray-500 uppercase">
                      Average score
                    </p>
                    <p className="mt-1 text-2xl font-bold text-gray-900">
                      {data?.summary.avg_quiz_score ?? 0}%
                    </p>
                    <p className="mt-1 text-xs text-gray-400">
                      across every quiz you finished
                    </p>
                  </CardContent>
                </Card>
              )}
            </>
          )}
        </div>

        <div className="grid gap-6 lg:grid-cols-3">
          {/* ── My subjects (question 3) ───────────────────────────────── */}
          <section className="lg:col-span-2">
            <h2 className="mb-3 text-lg font-semibold text-gray-900">My subjects</h2>
            {isLoading ? (
              <div className="space-y-2">
                {[...Array(3)].map((_, i) => (
                  <Skeleton key={i} className="h-16 rounded-lg" />
                ))}
              </div>
            ) : !data?.subject_progress.length ? (
              <EmptyState />
            ) : (
              <div className="space-y-2">
                {data.subject_progress.map((s) => (
                  <Card key={s.subject} className="border shadow-sm">
                    <CardContent className="p-4">
                      <div className="flex items-baseline justify-between gap-3">
                        <p className="text-sm font-medium text-gray-900">{s.subject}</p>
                        <p className="text-xs text-gray-500">
                          {s.units_completed} of {s.units_total} units
                          {/* null, not 0 — a student who has answered nothing
                              has not scored zero, and showing 0% reads as
                              failure rather than "not started". */}
                          {s.avg_score !== null && (
                            <span className="ml-2 font-medium text-gray-700">
                              · {s.avg_score}% avg
                            </span>
                          )}
                        </p>
                      </div>
                      <div
                        className="mt-2 h-2 w-full overflow-hidden rounded-full bg-gray-100"
                        role="progressbar"
                        aria-valuenow={Math.round(s.pct)}
                        aria-valuemin={0}
                        aria-valuemax={100}
                        aria-label={`${s.subject} progress`}
                      >
                        <div
                          className="h-full rounded-full bg-indigo-500"
                          style={{ width: `${Math.min(s.pct, 100)}%` }}
                        />
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </section>

          {/* ── What's next (question 1) ───────────────────────────────── */}
          <aside>
            <h2 className="mb-3 text-lg font-semibold text-gray-900">Up next</h2>
            {isLoading ? (
              <Skeleton className="h-40 rounded-lg" />
            ) : data?.next_unit ? (
              <Card className="border-indigo-100 bg-indigo-50">
                <CardContent className="space-y-3 p-4">
                  <p className="text-xs font-medium tracking-wide text-indigo-500 uppercase">
                    {data.next_unit.subject}
                  </p>
                  <p className="text-sm font-semibold text-indigo-900">
                    {data.next_unit.title}
                  </p>
                  <p className="flex items-center gap-1 text-xs text-indigo-600">
                    <Clock className="h-3 w-3" /> about {data.next_unit.estimated_minutes}{" "}
                    minutes
                  </p>
                  <LinkButton
                    href={`/lesson/${data.next_unit.unit_id}`}
                    className="w-full justify-center gap-2"
                  >
                    Start this unit <ArrowRight className="h-4 w-4" />
                  </LinkButton>
                </CardContent>
              </Card>
            ) : (
              <Card className="border-green-100 bg-green-50">
                <CardContent className="p-6 text-center">
                  <CheckCircle2 className="mx-auto mb-2 h-8 w-8 text-green-500" />
                  <p className="text-sm font-semibold text-green-800">
                    You&apos;ve passed every unit
                  </p>
                  <p className="mt-1 text-xs text-green-600">
                    Revisit any subject to push your scores up.
                  </p>
                </CardContent>
              </Card>
            )}

            <div className="mt-4 space-y-2">
              <LinkButton
                href="/subjects"
                variant="outline"
                className="w-full justify-start gap-2"
              >
                <BookOpen className="h-4 w-4" /> Browse Subjects
              </LinkButton>
              <LinkButton
                href="/curriculum"
                variant="outline"
                className="w-full justify-start gap-2"
              >
                <CheckCircle2 className="h-4 w-4" /> Curriculum Map
              </LinkButton>
              <LinkButton
                href="/progress"
                variant="outline"
                className="w-full justify-start gap-2"
              >
                <Clock className="h-4 w-4" /> View Progress
              </LinkButton>
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}

/** Curriculum total, summed from the per-subject rows the server resolved. */
function totalUnits(data: ReturnType<typeof useStudentDashboard>["data"]): number {
  return data?.subject_progress.reduce((n, s) => n + s.units_total, 0) ?? 0;
}

function EmptyState() {
  return (
    <div className="rounded-xl border border-indigo-100 bg-indigo-50 p-6 text-center">
      <Sparkles className="mx-auto mb-3 h-8 w-8 text-indigo-400" />
      <p className="mb-1 text-sm font-semibold text-indigo-800">Welcome to StudyBuddy!</p>
      <p className="mb-4 text-xs text-indigo-600">
        Your subjects will appear here as soon as your school sets up your curriculum.
      </p>
      <LinkButton href="/subjects" className="mx-auto w-fit text-xs">
        Browse Subjects
      </LinkButton>
    </div>
  );
}
