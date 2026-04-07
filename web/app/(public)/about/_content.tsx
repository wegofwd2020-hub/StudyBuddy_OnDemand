"use client";

import { useEffect, useState } from "react";
import {
  CheckCircle2,
  Clock,
  AlertCircle,
  BookOpen,
  Shield,
  Globe,
  FileText,
  Lock,
  GitPullRequest,
  ShieldCheck,
  ShieldAlert,
  Zap,
  Volume2,
  WifiOff,
  FlaskConical,
  School,
  GraduationCap,
  Users,
} from "lucide-react";
import Link from "next/link";
import {
  COMPLIANCE_STANDARDS,
  COMPLIANCE_CATEGORIES,
  type ComplianceStatus,
  type ComplianceStandard,
} from "@/lib/compliance";
import { LinkButton } from "@/components/ui/link-button";

export interface AboutBuildData {
  buildTime: string;
  snykHigh: string;
  snykCritical: string;
  snykScanDate: string;
  lastPrNumber: string;
  lastPrTitle: string;
  lastPrUrl: string;
  lastPrMergedAt: string;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatDate(iso: string | null): string {
  if (!iso) return "unknown";
  try {
    return new Date(iso).toLocaleDateString("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
      timeZone: "UTC",
    });
  } catch {
    return iso;
  }
}

function isLoggedIn(): boolean {
  if (typeof window === "undefined") return false;
  return !!(
    localStorage.getItem("sb_token") ||
    localStorage.getItem("sb_teacher_token") ||
    localStorage.getItem("sb_admin_token")
  );
}

// ── Compliance helpers ────────────────────────────────────────────────────────

const STATUS_META: Record<
  ComplianceStatus,
  { label: string; icon: React.ReactNode; className: string }
> = {
  compliant: {
    label: "Compliant",
    icon: <CheckCircle2 className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />,
    className: "bg-green-50 text-green-700",
  },
  targeted: {
    label: "Targeted",
    icon: <Clock className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />,
    className: "bg-blue-50 text-blue-700",
  },
  partial: {
    label: "Partial",
    icon: <AlertCircle className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />,
    className: "bg-amber-50 text-amber-700",
  },
};

const CATEGORY_ICONS: Record<ComplianceStandard["category"], React.ReactNode> = {
  Accessibility: <BookOpen className="h-5 w-5 text-blue-600" aria-hidden="true" />,
  "Privacy & Legal": <Shield className="h-5 w-5 text-purple-600" aria-hidden="true" />,
  Security: <Lock className="h-5 w-5 text-red-500" aria-hidden="true" />,
  Content: <FileText className="h-5 w-5 text-emerald-600" aria-hidden="true" />,
  Internationalisation: <Globe className="h-5 w-5 text-orange-500" aria-hidden="true" />,
};

function StatusBadge({ status }: { status: ComplianceStatus }) {
  const { label, icon, className } = STATUS_META[status];
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium ${className}`}
    >
      {icon}
      {label}
    </span>
  );
}

// ── Snyk security panel ───────────────────────────────────────────────────────

function SnykPanel({
  snykHigh,
  snykCritical,
  snykScanDate,
}: Pick<AboutBuildData, "snykHigh" | "snykCritical" | "snykScanDate">) {
  const scanned = snykScanDate !== "";
  const high = snykHigh !== "" ? parseInt(snykHigh, 10) : null;
  const critical = snykCritical !== "" ? parseInt(snykCritical, 10) : null;
  const clean = high === 0 && critical === 0;

  return (
    <section
      aria-labelledby="snyk-heading"
      className="rounded-xl border border-gray-200 bg-white p-6"
    >
      <div className="mb-4 flex items-center gap-2">
        {scanned && clean ? (
          <ShieldCheck className="h-5 w-5 text-green-600" aria-hidden="true" />
        ) : scanned ? (
          <ShieldAlert className="h-5 w-5 text-red-500" aria-hidden="true" />
        ) : (
          <Shield className="h-5 w-5 text-gray-400" aria-hidden="true" />
        )}
        <h2 id="snyk-heading" className="text-lg font-semibold text-gray-900">
          Dependency Security
        </h2>
      </div>

      {!scanned ? (
        <p className="text-sm text-gray-500">
          Snyk scan results are not available in this environment. Scans run automatically
          on every CI build when{" "}
          <code className="rounded bg-gray-100 px-1 py-0.5 text-xs">SNYK_TOKEN</code> is
          configured.
        </p>
      ) : (
        <>
          <div className="mb-4 flex flex-wrap items-center gap-6">
            <div>
              <p
                className={`text-3xl font-bold ${
                  critical !== null && critical > 0 ? "text-red-600" : "text-gray-900"
                }`}
              >
                {critical ?? "—"}
              </p>
              <p className="mt-0.5 text-xs text-gray-500">Critical vulnerabilities</p>
            </div>
            <div className="h-10 w-px bg-gray-200" aria-hidden="true" />
            <div>
              <p
                className={`text-3xl font-bold ${
                  high !== null && high > 0 ? "text-amber-600" : "text-gray-900"
                }`}
              >
                {high ?? "—"}
              </p>
              <p className="mt-0.5 text-xs text-gray-500">High vulnerabilities</p>
            </div>
            <div className="h-10 w-px bg-gray-200" aria-hidden="true" />
            <div>
              {clean ? (
                <span className="inline-flex items-center gap-1.5 rounded-full bg-green-50 px-3 py-1 text-sm font-medium text-green-700">
                  <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
                  No high or critical issues
                </span>
              ) : (
                <span className="inline-flex items-center gap-1.5 rounded-full bg-red-50 px-3 py-1 text-sm font-medium text-red-700">
                  <AlertCircle className="h-4 w-4" aria-hidden="true" />
                  Issues require attention
                </span>
              )}
            </div>
          </div>
          <p className="text-xs text-gray-400">
            Scanned across Python (backend) and Node.js (frontend) dependencies
            {snykScanDate && (
              <>
                {" · "}
                <time dateTime={snykScanDate}>Last scan: {formatDate(snykScanDate)}</time>
              </>
            )}
          </p>
        </>
      )}
    </section>
  );
}

// ── Last release panel ────────────────────────────────────────────────────────

function LastReleasePanel({
  lastPrNumber,
  lastPrTitle,
  lastPrUrl,
  lastPrMergedAt,
}: Pick<
  AboutBuildData,
  "lastPrNumber" | "lastPrTitle" | "lastPrUrl" | "lastPrMergedAt"
>) {
  const hasData = lastPrNumber !== "" && lastPrTitle !== "";

  return (
    <section
      aria-labelledby="release-heading"
      className="rounded-xl border border-gray-200 bg-white p-6"
    >
      <div className="mb-4 flex items-center gap-2">
        <GitPullRequest className="h-5 w-5 text-indigo-600" aria-hidden="true" />
        <h2 id="release-heading" className="text-lg font-semibold text-gray-900">
          Last Published Release
        </h2>
      </div>

      {!hasData ? (
        <p className="text-sm text-gray-500">
          Release information is not available in this environment. It is injected at
          build time during CI deployment.
        </p>
      ) : (
        <div className="space-y-3">
          <div className="flex flex-wrap items-start gap-3">
            <span className="mt-0.5 inline-flex shrink-0 items-center rounded-full bg-indigo-50 px-2.5 py-1 text-xs font-medium text-indigo-700">
              #{lastPrNumber}
            </span>
            {lastPrUrl ? (
              <Link
                href={lastPrUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-base font-medium text-gray-900 underline-offset-2 hover:text-indigo-600 hover:underline"
              >
                {lastPrTitle}
              </Link>
            ) : (
              <p className="text-base font-medium text-gray-900">{lastPrTitle}</p>
            )}
          </div>
          {lastPrMergedAt && (
            <p className="text-xs text-gray-400">
              Merged <time dateTime={lastPrMergedAt}>{formatDate(lastPrMergedAt)}</time>
            </p>
          )}
        </div>
      )}
    </section>
  );
}

// ── Authenticated view (full build + compliance data) ─────────────────────────

function AuthenticatedAbout({ data }: { data: AboutBuildData }) {
  const byCategory = COMPLIANCE_CATEGORIES.map((cat) => ({
    category: cat,
    standards: COMPLIANCE_STANDARDS.filter((s) => s.category === cat),
  }));

  const compliantCount = COMPLIANCE_STANDARDS.filter(
    (s) => s.status === "compliant",
  ).length;
  const totalCount = COMPLIANCE_STANDARDS.length;

  return (
    <div className="mx-auto max-w-5xl px-4 py-16 sm:px-6 lg:px-8">
      <div className="mb-12">
        <h1 className="text-4xl font-bold tracking-tight text-gray-900">
          About StudyBuddy
        </h1>
        <p className="mt-4 max-w-2xl text-lg text-gray-600">
          StudyBuddy is an AI-powered learning platform for Grades 5–12. Lessons,
          quizzes, and audio are pre-generated so students get instant responses — no API
          keys, no wait time, and no internet required for cached content.
        </p>
      </div>

      {/* Security + Release row */}
      <div className="mb-10 grid gap-6 sm:grid-cols-2">
        <SnykPanel
          snykHigh={data.snykHigh}
          snykCritical={data.snykCritical}
          snykScanDate={data.snykScanDate}
        />
        <LastReleasePanel
          lastPrNumber={data.lastPrNumber}
          lastPrTitle={data.lastPrTitle}
          lastPrUrl={data.lastPrUrl}
          lastPrMergedAt={data.lastPrMergedAt}
        />
      </div>

      {/* Compliance summary strip */}
      <div className="mb-10 flex flex-wrap items-center gap-6 rounded-2xl border border-gray-100 bg-gray-50 px-6 py-5">
        <div>
          <p className="text-2xl font-bold text-gray-900">
            {compliantCount}
            <span className="text-base font-normal text-gray-500"> / {totalCount}</span>
          </p>
          <p className="text-sm text-gray-500">standards compliant</p>
        </div>
        <div className="h-10 w-px bg-gray-200" aria-hidden="true" />
        <div>
          <p className="text-2xl font-bold text-gray-900">
            {COMPLIANCE_CATEGORIES.length}
          </p>
          <p className="text-sm text-gray-500">compliance categories</p>
        </div>
        <div className="h-10 w-px bg-gray-200" aria-hidden="true" />
        <div>
          <p className="text-sm font-medium text-gray-700">Standards verified as of</p>
          <p className="text-sm text-gray-500">
            {formatDate(data.buildTime || null)} build
          </p>
        </div>
        <div className="ml-auto flex flex-wrap gap-3">
          {(["compliant", "targeted", "partial"] as ComplianceStatus[]).map((s) => (
            <StatusBadge key={s} status={s} />
          ))}
        </div>
      </div>

      {/* Standards table per category */}
      <div className="space-y-12">
        {byCategory.map(({ category, standards }) => (
          <section key={category} aria-labelledby={`cat-${category}`}>
            <div className="mb-4 flex items-center gap-2">
              {CATEGORY_ICONS[category]}
              <h2 id={`cat-${category}`} className="text-xl font-semibold text-gray-900">
                {category}
              </h2>
            </div>

            <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white">
              <table
                className="w-full text-sm"
                aria-label={`${category} compliance standards`}
              >
                <thead>
                  <tr className="border-b border-gray-100 bg-gray-50 text-left">
                    <th className="px-5 py-3 text-xs font-medium tracking-wide text-gray-500 uppercase">
                      Standard
                    </th>
                    <th className="px-5 py-3 text-xs font-medium tracking-wide text-gray-500 uppercase">
                      Version / Updated
                    </th>
                    <th className="px-5 py-3 text-xs font-medium tracking-wide text-gray-500 uppercase">
                      Description
                    </th>
                    <th className="px-5 py-3 text-xs font-medium tracking-wide text-gray-500 uppercase">
                      Status
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {standards.map((s) => (
                    <tr key={s.standard} className="hover:bg-gray-50">
                      <td className="px-5 py-4 align-top font-medium whitespace-nowrap text-gray-900">
                        {s.standard}
                      </td>
                      <td className="px-5 py-4 align-top whitespace-nowrap text-gray-500">
                        {s.version}
                      </td>
                      <td className="max-w-md px-5 py-4 align-top text-gray-600">
                        {s.description}
                      </td>
                      <td className="px-5 py-4 align-top">
                        <StatusBadge status={s.status} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        ))}
      </div>

      {/* Status legend */}
      <div className="mt-12 rounded-xl border border-gray-100 bg-gray-50 px-6 py-5">
        <h2 className="mb-3 text-sm font-semibold text-gray-700">Status definitions</h2>
        <dl className="space-y-2 text-sm">
          <div className="flex items-start gap-3">
            <StatusBadge status="compliant" />
            <dd className="text-gray-600">
              Implemented and verified in code. Automated or manual tests confirm the
              behaviour.
            </dd>
          </div>
          <div className="flex items-start gap-3">
            <StatusBadge status="targeted" />
            <dd className="text-gray-600">
              Actively targeted. Core infrastructure is in place; automated coverage is
              being expanded across all pages and flows.
            </dd>
          </div>
          <div className="flex items-start gap-3">
            <StatusBadge status="partial" />
            <dd className="text-gray-600">
              Partially implemented. Some flows are covered; remaining gaps are tracked
              and scheduled.
            </dd>
          </div>
        </dl>
      </div>

      <p className="mt-8 text-center text-xs text-gray-400">
        This page is generated at build time.{" "}
        {data.buildTime && (
          <>
            Last deployment:{" "}
            <time dateTime={data.buildTime}>{formatDate(data.buildTime)}</time>.{" "}
          </>
        )}
        Standards data is sourced from{" "}
        <code className="rounded bg-gray-100 px-1 py-0.5">web/lib/compliance.ts</code>.
      </p>
    </div>
  );
}

// ── Public product description view ──────────────────────────────────────────

const FEATURES = [
  {
    icon: <Zap className="h-6 w-6 text-blue-600" />,
    title: "Instant content",
    desc: "Pre-generated lessons and quizzes load in milliseconds — no AI wait time, ever.",
  },
  {
    icon: <Volume2 className="h-6 w-6 text-purple-600" />,
    title: "Audio lessons",
    desc: "Every lesson has a narrated audio version. Students can learn by reading or listening.",
  },
  {
    icon: <Globe className="h-6 w-6 text-orange-500" />,
    title: "English, French & Spanish",
    desc: "Full curriculum content in three languages. Students switch any time in settings.",
  },
  {
    icon: <WifiOff className="h-6 w-6 text-gray-600" />,
    title: "Works offline",
    desc: "Downloaded content is available without internet. Progress syncs automatically when back online.",
  },
  {
    icon: <FlaskConical className="h-6 w-6 text-emerald-600" />,
    title: "Activities",
    desc: "Step-by-step activity guides with materials lists bring hands-on learning to any classroom.",
  },
  {
    icon: <School className="h-6 w-6 text-indigo-600" />,
    title: "Built for schools",
    desc: "Teachers upload their own curriculum, track class progress in real time, and set alerts.",
  },
  {
    icon: <GraduationCap className="h-6 w-6 text-cyan-600" />,
    title: "Teacher tools",
    desc: "Six report types, CSV export, weekly digest emails, and a full class dashboard.",
  },
  {
    icon: <Users className="h-6 w-6 text-pink-600" />,
    title: "Student & school management",
    desc: "Enrol students, manage class rosters, and track individual progress across all subjects.",
  },
  {
    icon: <Shield className="h-6 w-6 text-red-500" />,
    title: "Privacy-first",
    desc: "COPPA and FERPA compliant. Minimum necessary data collection, no tracking, no behavioural fingerprinting.",
  },
] as const;

const STATS = [
  { value: "Grades 5–12", label: "Target audience" },
  { value: "3 Languages", label: "English, French & Spanish" },
  { value: "48h", label: "Teacher demo duration" },
  { value: "24h", label: "Student demo duration" },
] as const;

function PublicAbout() {
  return (
    <div className="mx-auto max-w-5xl px-4 py-16 sm:px-6 lg:px-8">
      {/* Hero */}
      <div className="mb-16 text-center">
        <h1 className="text-4xl font-bold tracking-tight text-gray-900 sm:text-5xl">
          About StudyBuddy
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-lg text-gray-600">
          An AI-powered study material platform for Grades 5–12. Lessons, quizzes, and
          audio are pre-generated so students get instant responses — no wait time, no
          internet required for cached content.
        </p>
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          <LinkButton href="/signup" size="lg">
            Start free trial
          </LinkButton>
          <LinkButton href="/" size="lg" variant="outline">
            See a demo
          </LinkButton>
        </div>
      </div>

      {/* Stats strip */}
      <div className="mb-16 grid grid-cols-2 gap-px overflow-hidden rounded-2xl border border-gray-200 bg-gray-200 sm:grid-cols-4">
        {STATS.map(({ value, label }) => (
          <div key={label} className="bg-white px-6 py-8 text-center">
            <p className="text-2xl font-bold text-gray-900">{value}</p>
            <p className="mt-1 text-sm text-gray-500">{label}</p>
          </div>
        ))}
      </div>

      {/* Mission */}
      <div className="mb-16 rounded-2xl bg-blue-600 px-8 py-10 text-white">
        <h2 className="mb-4 text-2xl font-bold">Our mission</h2>
        <p className="max-w-2xl text-blue-100">
          Every student deserves access to high-quality education regardless of their
          internet connection, device, or first language. StudyBuddy delivers AI-generated
          study material to students the moment they need it — with audio support for
          accessibility and offline caching for low-connectivity environments.
        </p>
      </div>

      {/* Features grid */}
      <div className="mb-16">
        <h2 className="mb-8 text-2xl font-bold text-gray-900">What StudyBuddy offers</h2>
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map(({ icon, title, desc }) => (
            <div
              key={title}
              className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm"
            >
              <div className="mb-3 flex h-11 w-11 items-center justify-center rounded-lg bg-gray-50">
                {icon}
              </div>
              <h3 className="font-semibold text-gray-900">{title}</h3>
              <p className="mt-1.5 text-sm text-gray-500">{desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* How it works */}
      <div className="mb-16">
        <h2 className="mb-8 text-2xl font-bold text-gray-900">How it works</h2>
        <ol className="space-y-6">
          {[
            {
              step: "1",
              title: "Teacher sets up the class",
              body: "A teacher or school admin registers the school, uploads their curriculum (or uses the default curriculum), and invites students.",
            },
            {
              step: "2",
              title: "Content is pre-generated",
              body: "Our pipeline runs Claude to generate lessons, quizzes, tutorials, and audio for every unit in every active language. Content is cached on the CDN.",
            },
            {
              step: "3",
              title: "Students learn on any device",
              body: "Students open the app, select a unit, and get instant content — text, audio, and interactive quizzes. Progress is recorded and synced back to the teacher dashboard.",
            },
            {
              step: "4",
              title: "Teachers track and adapt",
              body: "Real-time dashboards show quiz scores, session times, and completion rates. Teachers receive weekly digest emails and can set alert thresholds for struggling students.",
            },
          ].map(({ step, title, body }) => (
            <li key={step} className="flex gap-5">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-blue-600 text-sm font-bold text-white">
                {step}
              </div>
              <div>
                <p className="font-semibold text-gray-900">{title}</p>
                <p className="mt-1 text-sm text-gray-600">{body}</p>
              </div>
            </li>
          ))}
        </ol>
      </div>

      {/* Compliance callout */}
      <div className="rounded-2xl border border-gray-200 bg-gray-50 px-8 py-8">
        <div className="flex items-start gap-4">
          <Shield
            className="mt-0.5 h-6 w-6 shrink-0 text-purple-600"
            aria-hidden="true"
          />
          <div>
            <h2 className="mb-2 text-lg font-semibold text-gray-900">
              Compliance &amp; accessibility
            </h2>
            <p className="text-sm text-gray-600">
              StudyBuddy targets <strong>WCAG 2.1 Level AA</strong> for all student-facing
              interfaces, and is built to comply with <strong>COPPA</strong> (parental
              consent for under-13 students) and <strong>FERPA</strong> (educational
              record privacy). Full compliance details, including per-standard status, are
              available to signed-in users on this page.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Root export ───────────────────────────────────────────────────────────────

export function AboutContent({ data }: { data: AboutBuildData }) {
  // null = not yet determined (avoids flash of wrong content)
  const [authenticated, setAuthenticated] = useState<boolean | null>(null);

  useEffect(() => {
    setAuthenticated(isLoggedIn());
  }, []);

  // Brief invisible state while localStorage is being read — avoids layout flash
  if (authenticated === null) {
    return <div className="min-h-[60vh]" aria-hidden="true" />;
  }

  return authenticated ? <AuthenticatedAbout data={data} /> : <PublicAbout />;
}
