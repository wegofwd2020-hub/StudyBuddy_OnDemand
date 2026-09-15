"use client";

import Image from "next/image";
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useTeacher } from "@/lib/hooks/useTeacher";
import {
  getOverviewReport,
  getAlerts,
  getClassMetrics,
  type ReportPeriod,
} from "@/lib/api/reports";
import { listTeachers, getLibrary } from "@/lib/api/school-admin";
import { SetupChecklist } from "@/components/school/SetupChecklist";
import { NoGradesNotice, ScopeNote } from "@/components/school/ScopeNote";
import { CommercialStrip } from "@/components/school/CommercialStrip";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { LinkButton } from "@/components/ui/link-button";
import { Badge } from "@/components/ui/badge";
import { useSchoolTheme } from "@/lib/theme/SchoolThemeContext";
import { getSubjectPalette } from "@/lib/theme/getSubjectPalette";
import { SUBJECT_ORDER } from "@/lib/theme/defaults";
import { cn } from "@/lib/utils";
import {
  Users,
  BookOpen,
  CheckCircle,
  Bell,
  TrendingUp,
  AlertTriangle,
  GraduationCap,
  LayoutGrid,
  BookMarked,
  LineChart,
  BarChart2,
  MessageSquare,
  Download,
} from "lucide-react";

// The backend overview endpoint only accepts these three values
// (`backend/src/reports/router.py`, `^(7d|30d|term)$`) — the student stats
// endpoint's vocabulary ("7d"/"30d"/"all") is a different set (an "all time"
// window has no equivalent here; a school "term" window has no equivalent
// there), so the admin selector is deliberately constrained to what this
// endpoint supports rather than inventing values the API would reject.
const OVERVIEW_PERIODS: { value: ReportPeriod; label: string }[] = [
  { value: "7d", label: "Last 7 days" },
  { value: "30d", label: "Last 30 days" },
  { value: "term", label: "This term" },
];

const OVERVIEW_PERIOD_LABELS: Record<ReportPeriod, string> = {
  "7d": "the last 7 days",
  "30d": "the last 30 days",
  term: "this term",
};

function KpiCard({
  title,
  value,
  subtitle,
  icon,
  accent,
}: {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ReactNode;
  accent?: "green" | "blue" | "red" | "gray";
}) {
  const colors = {
    green: "text-green-600 bg-green-50",
    blue: "text-blue-600 bg-blue-50",
    red: "text-red-500 bg-red-50",
    gray: "text-gray-500 bg-gray-100",
  };
  return (
    <Card className="border shadow-sm">
      <CardContent className="flex items-start gap-4 p-5">
        <div className={`rounded-lg p-2.5 ${colors[accent ?? "blue"]}`}>{icon}</div>
        <div>
          <p className="text-xs font-medium tracking-wide text-gray-400 uppercase">
            {title}
          </p>
          <p className="mt-0.5 text-2xl font-bold text-gray-900">{value}</p>
          {subtitle && <p className="mt-0.5 text-xs text-gray-500">{subtitle}</p>}
        </div>
      </CardContent>
    </Card>
  );
}

/**
 * Themed welcome band (#366). Uses the school's primary accent for a soft
 * gradient and shows the school identity (logo where set, else name) alongside
 * the banyan brand image — replacing the previous flat, floating hero so the
 * first thing a user sees reads as a designed surface, not a wall of text.
 */
function WelcomeHero({
  name,
  logoUrl,
  accent,
  children,
}: {
  name: string;
  logoUrl: string | null;
  accent: string;
  children?: React.ReactNode;
}) {
  const p = getSubjectPalette(accent);
  return (
    <div
      className="relative overflow-hidden rounded-2xl border"
      style={{
        borderColor: p.border,
        background: `linear-gradient(120deg, ${p.bg1} 0%, #ffffff 65%)`,
      }}
    >
      <div className="flex items-center justify-between gap-4 px-6 py-5">
        <div className="flex items-center gap-4">
          {logoUrl ? (
            // Plain img: school logos are arbitrary remote URLs, so we avoid
            // next/image's domain allow-list requirement here.
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={logoUrl}
              alt={`${name} logo`}
              className="h-12 w-12 rounded-lg object-contain"
            />
          ) : null}
          <div>
            <p
              className="text-xs font-semibold tracking-wide uppercase"
              style={{ color: p.ink }}
            >
              Welcome back
            </p>
            <h1 className="text-2xl font-bold text-gray-900">{name}</h1>
            {/* No fixed window here on purpose — the overview card below has
                its own period selector, and duplicating "this week" here
                would go stale (and lie) the moment that selector moves off
                its default. */}
            <p className="mt-0.5 text-sm text-gray-500">
              Here&apos;s how your school is doing.
            </p>
            {children && <div className="mt-3 flex flex-wrap gap-2">{children}</div>}
          </div>
        </div>
        <div className="relative hidden h-24 w-36 shrink-0 sm:block">
          <Image
            src="/assets/banyan_tree.png"
            alt=""
            fill
            priority
            className="object-contain object-right"
          />
        </div>
      </div>
    </div>
  );
}

/** A colored, scannable shortcut tile — replaces the plain text-button row. */
function ActionTile({
  href,
  label,
  icon,
  accent,
}: {
  href: string;
  label: string;
  icon: React.ReactNode;
  accent: string;
}) {
  const p = getSubjectPalette(accent);
  return (
    <Link
      href={href}
      className="group flex items-center gap-3 rounded-xl border bg-white p-4 shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md"
      style={{ borderColor: p.border }}
    >
      <span
        className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg"
        style={{ backgroundColor: p.bg1, color: p.accent }}
      >
        {icon}
      </span>
      <span className="text-sm font-medium text-gray-700 group-hover:text-gray-900">
        {label}
      </span>
    </Link>
  );
}

export default function SchoolDashboard() {
  const teacher = useTeacher();
  const schoolId = teacher?.school_id ?? "";
  const theme = useSchoolTheme();
  // Cycle the school's subject accents so tiles pick up per-school theming.
  const accents = SUBJECT_ORDER.map((k) => theme.subjects[k]?.accent ?? "#4f46e5");
  const primaryAccent = accents[1] ?? "#4f46e5"; // Math accent — the brand indigo by default

  // Defaults to "30d" to match the student stats page (`/stats`) default —
  // so the two screens agree out of the box instead of silently comparing
  // different windows. This selector governs ONLY the overview query below;
  // alerts, library, teachers, and class-metrics are not period-scoped.
  const [period, setPeriod] = useState<ReportPeriod>("30d");

  const { data: overview, isLoading } = useQuery({
    queryKey: ["report-overview", schoolId, period],
    queryFn: () => getOverviewReport(schoolId, period),
    enabled: !!schoolId,
    staleTime: 120_000,
  });

  const { data: alertsData } = useQuery({
    queryKey: ["alerts", schoolId],
    queryFn: () => getAlerts(schoolId),
    enabled: !!schoolId,
    staleTime: 60_000,
  });

  const unreadAlerts = alertsData?.alerts?.filter((a) => !a.acknowledged).length ?? 0;

  const isAdmin = teacher?.role === "school_admin";

  const { data: libraryData } = useQuery({
    queryKey: ["library", schoolId],
    queryFn: () => getLibrary(schoolId),
    enabled: !!schoolId && isAdmin,
    staleTime: 120_000,
  });

  const hasNoLibrary = isAdmin && libraryData !== undefined && libraryData.total === 0;

  const { data: teachers } = useQuery({
    queryKey: ["teachers", schoolId],
    queryFn: () => listTeachers(schoolId),
    enabled: !!schoolId && !isAdmin,
    staleTime: 30_000,
  });

  const assignedGrades = useMemo(() => {
    if (isAdmin || !teachers || !teacher?.teacher_id) return null;
    const me = teachers.find((t) => t.teacher_id === teacher.teacher_id);
    return me?.assigned_grades ?? [];
  }, [teachers, teacher, isAdmin]);

  const { data: classMetrics } = useQuery({
    queryKey: ["class-metrics", schoolId],
    queryFn: () => getClassMetrics(schoolId),
    enabled: !!schoolId && !isAdmin && (assignedGrades?.length ?? 0) > 0,
    staleTime: 60_000,
  });

  return (
    <div className="flex flex-col">
      <div className="max-w-6xl space-y-6 p-6">
        {/* Themed welcome band (#366) — school identity + brand image + actions */}
        <WelcomeHero
          name={theme.school.name}
          logoUrl={theme.school.logoUrl}
          accent={primaryAccent}
        >
          {unreadAlerts > 0 && (
            <LinkButton href="/school/alerts" variant="outline" size="sm">
              <Bell className="mr-1.5 h-4 w-4 text-red-500" />
              {unreadAlerts} alert{unreadAlerts !== 1 ? "s" : ""}
            </LinkButton>
          )}
          <LinkButton href="/school/reports/overview" size="sm">
            View full report
          </LinkButton>
        </WelcomeHero>

        {/* Headline stats first (#368 VT-1) — kept directly under the hero so the
            KPIs land in the first viewport without scrolling. Onboarding and
            secondary cards follow below.
            The period selector is scoped visually to this card group only —
            it must not read as filtering the alerts/library/teacher/class
            sections further down the page, none of which take a period. */}
        <div>
          <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <h2 className="text-sm font-semibold tracking-wide text-gray-500 uppercase">
                  Overview
                </h2>
                {/* WHO the numbers cover, next to WHEN they cover (#640, §10).
                    A teacher's figures mean their grades and an admin's mean
                    the school — the page said neither, which is the defect the
                    dashboard redesign was actually reported for. */}
                <ScopeNote scope={overview?.scope} />
              </div>
              <p className="mt-0.5 text-xs text-gray-400">
                Showing {OVERVIEW_PERIOD_LABELS[period]}. Only these cards change with the
                selector — alerts and other sections below are not filtered by it.
              </p>
            </div>
            <div className="flex gap-1 rounded-lg border bg-white p-1">
              {OVERVIEW_PERIODS.map((p) => (
                <button
                  key={p.value}
                  onClick={() => setPeriod(p.value)}
                  className={cn(
                    "rounded px-3 py-1 text-xs font-medium transition-colors",
                    period === p.value
                      ? "bg-blue-600 text-white"
                      : "text-gray-500 hover:text-gray-900",
                  )}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>

          <div className="mb-3">
            <NoGradesNotice scope={overview?.scope} />
          </div>

          {isLoading ? (
            <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
              {Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} className="h-28 rounded-lg" />
              ))}
            </div>
          ) : overview ? (
            <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
              <KpiCard
                title="Enrolled students"
                value={overview.enrolled_students}
                icon={<Users className="h-5 w-5" />}
                accent="blue"
              />
              <KpiCard
                title="Active"
                value={
                  overview.active_pct != null ? `${overview.active_pct.toFixed(0)}%` : "—"
                }
                subtitle={`${overview.active_students_period ?? 0} of ${overview.enrolled_students ?? 0} — ${OVERVIEW_PERIOD_LABELS[period]}`}
                icon={<TrendingUp className="h-5 w-5" />}
                accent="green"
              />
              <KpiCard
                title="Lessons viewed"
                value={overview.lessons_viewed}
                subtitle={OVERVIEW_PERIODS.find((p) => p.value === period)?.label}
                icon={<BookOpen className="h-5 w-5" />}
                accent="blue"
              />
              <KpiCard
                title="Pass rate (1st attempt)"
                value={
                  overview.first_attempt_pass_rate_pct != null
                    ? `${overview.first_attempt_pass_rate_pct.toFixed(0)}%`
                    : "—"
                }
                icon={<CheckCircle className="h-5 w-5" />}
                accent={
                  overview.first_attempt_pass_rate_pct != null &&
                  overview.first_attempt_pass_rate_pct >= 60
                    ? "green"
                    : "red"
                }
              />
              <KpiCard
                title="Quiz attempts"
                value={overview.quiz_attempts}
                icon={<BookOpen className="h-5 w-5" />}
                accent="gray"
              />
              <KpiCard
                title="Unreviewed feedback"
                value={overview.unreviewed_feedback_count}
                icon={<Bell className="h-5 w-5" />}
                accent={overview.unreviewed_feedback_count > 0 ? "red" : "gray"}
              />
            </div>
          ) : null}
        </div>

        {/* Layer 1.5 — first-run setup checklist (school_admin only) */}
        {isAdmin && schoolId && <SetupChecklist schoolId={schoolId} />}

        {/* Seats / storage / build runs (#640, C3a) — the questions that end in
            a bill or a blocked action. school_admin only: a teacher cannot act
            on them. */}
        {isAdmin && schoolId && <CommercialStrip schoolId={schoolId} />}

        {/* Empty library nudge — shown to school_admin when no curricula adopted yet */}
        {hasNoLibrary && (
          <Card className="border border-indigo-100 bg-indigo-50 shadow-sm">
            <CardContent className="flex items-start gap-4 p-5">
              <div className="rounded-lg bg-indigo-100 p-2.5">
                <BookMarked className="h-5 w-5 text-indigo-600" />
              </div>
              <div className="flex-1">
                <p className="font-semibold text-indigo-900">
                  Your curriculum library is empty
                </p>
                <p className="mt-0.5 text-sm text-indigo-700">
                  Browse the platform catalog and add curricula to your library so
                  teachers can import and customize content for their classes.
                </p>
                <div className="mt-3 flex gap-2">
                  <LinkButton href="/school/catalog" size="sm">
                    <LayoutGrid className="mr-1.5 h-4 w-4" />
                    Browse catalog
                  </LinkButton>
                  <LinkButton href="/school/library" variant="outline" size="sm">
                    View library
                  </LinkButton>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* My Classes — shown for non-admin teachers with assigned grades */}
        {!isAdmin && assignedGrades && assignedGrades.length > 0 && (
          <section>
            <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold tracking-wide text-gray-500 uppercase">
              <GraduationCap className="h-4 w-4" />
              My Classes
            </h2>
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
              {assignedGrades.map((grade) => {
                const studentCount =
                  classMetrics?.students.filter((s) => s.grade === grade).length ?? 0;
                return (
                  <div key={grade} className="rounded-lg border bg-white p-4 shadow-sm">
                    <p className="text-3xl font-bold text-indigo-600">{grade}</p>
                    <p className="text-xs font-medium text-gray-400 uppercase">Grade</p>
                    <p className="mt-2 text-sm text-gray-600">
                      {studentCount} student{studentCount !== 1 ? "s" : ""}
                    </p>
                    <div className="mt-3 flex gap-2">
                      <Link
                        href="/school/curriculum/content"
                        className="flex-1 rounded-md bg-indigo-50 px-2 py-1.5 text-center text-xs font-medium text-indigo-700 hover:bg-indigo-100"
                      >
                        Content
                      </Link>
                      <Link
                        href="/school/students"
                        className="flex-1 rounded-md bg-gray-50 px-2 py-1.5 text-center text-xs font-medium text-gray-600 hover:bg-gray-100"
                      >
                        Students
                      </Link>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        )}

        {overview &&
          overview.units_with_struggles &&
          overview.units_with_struggles.length > 0 && (
            <Card className="border shadow-sm">
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-base">
                  <AlertTriangle className="h-4 w-4 text-orange-500" />
                  Units needing attention
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-2">
                  {overview.units_with_struggles.map((uid) => (
                    <Badge
                      key={uid}
                      className="border-orange-200 bg-orange-50 text-orange-700"
                    >
                      {uid}
                    </Badge>
                  ))}
                </div>
                <LinkButton
                  href="/school/reports/at-risk"
                  variant="outline"
                  size="sm"
                  className="mt-3"
                >
                  View at-risk report
                </LinkButton>
              </CardContent>
            </Card>
          )}

        <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
          {[
            {
              label: "Student progress",
              href: "/school/class/all",
              icon: <LineChart className="h-5 w-5" />,
            },
            {
              label: "Trends report",
              href: "/school/reports/trends",
              icon: <TrendingUp className="h-5 w-5" />,
            },
            {
              label: "Unit performance",
              href: "/school/reports/units",
              icon: <BarChart2 className="h-5 w-5" />,
            },
            {
              label: "Student feedback",
              href: "/school/reports/feedback",
              icon: <MessageSquare className="h-5 w-5" />,
            },
            {
              label: "Export CSV",
              href: "/school/reports/export",
              icon: <Download className="h-5 w-5" />,
            },
            {
              label: "Alert inbox",
              href: "/school/alerts",
              icon: <Bell className="h-5 w-5" />,
            },
          ].map((link, i) => (
            <ActionTile
              key={link.href}
              href={link.href}
              label={link.label}
              icon={link.icon}
              accent={accents[i % accents.length]}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
