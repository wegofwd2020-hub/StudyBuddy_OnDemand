import type { Metadata } from "next";
import { CheckCircle2, Clock, AlertCircle, BookOpen, Shield, Globe, FileText } from "lucide-react";
import {
  COMPLIANCE_STANDARDS,
  COMPLIANCE_CATEGORIES,
  type ComplianceStatus,
  type ComplianceStandard,
} from "@/lib/compliance";

export const metadata: Metadata = {
  title: "About",
  description:
    "About StudyBuddy — our mission, the accessibility and privacy standards we target, and how every build is verified.",
};

// Build time is stamped by next.config.ts at compile time.
const BUILD_TIME = process.env.NEXT_PUBLIC_BUILD_TIME ?? null;

function formatBuildTime(iso: string | null): string {
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

export default function AboutPage() {
  const byCategory = COMPLIANCE_CATEGORIES.map((cat) => ({
    category: cat,
    standards: COMPLIANCE_STANDARDS.filter((s) => s.category === cat),
  }));

  const compliantCount = COMPLIANCE_STANDARDS.filter((s) => s.status === "compliant").length;
  const totalCount = COMPLIANCE_STANDARDS.length;

  return (
    <div className="mx-auto max-w-5xl px-4 py-16 sm:px-6 lg:px-8">
      {/* Page header */}
      <div className="mb-12">
        <h1 className="text-4xl font-bold tracking-tight text-gray-900">About StudyBuddy</h1>
        <p className="mt-4 max-w-2xl text-lg text-gray-600">
          StudyBuddy is an AI-powered STEM tutoring platform for Grades 5–12. Lessons, quizzes,
          and audio are pre-generated so students get instant responses — no API keys, no wait
          time, and no internet required for cached content.
        </p>
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
          <p className="text-2xl font-bold text-gray-900">{COMPLIANCE_CATEGORIES.length}</p>
          <p className="text-sm text-gray-500">compliance categories</p>
        </div>
        <div className="h-10 w-px bg-gray-200" aria-hidden="true" />
        <div>
          <p className="text-sm font-medium text-gray-700">Standards verified as of</p>
          <p className="text-sm text-gray-500">{formatBuildTime(BUILD_TIME)} build</p>
        </div>

        {/* Legend */}
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
              <h2
                id={`cat-${category}`}
                className="text-xl font-semibold text-gray-900"
              >
                {category}
              </h2>
            </div>

            <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white">
              <table className="w-full text-sm" aria-label={`${category} compliance standards`}>
                <thead>
                  <tr className="border-b border-gray-100 bg-gray-50 text-left">
                    <th className="px-5 py-3 text-xs font-medium uppercase tracking-wide text-gray-500">
                      Standard
                    </th>
                    <th className="px-5 py-3 text-xs font-medium uppercase tracking-wide text-gray-500">
                      Version / Updated
                    </th>
                    <th className="px-5 py-3 text-xs font-medium uppercase tracking-wide text-gray-500">
                      Description
                    </th>
                    <th className="px-5 py-3 text-xs font-medium uppercase tracking-wide text-gray-500">
                      Status
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {standards.map((s) => (
                    <tr key={s.standard} className="hover:bg-gray-50">
                      <td className="px-5 py-4 font-medium text-gray-900 align-top whitespace-nowrap">
                        {s.standard}
                      </td>
                      <td className="px-5 py-4 text-gray-500 align-top whitespace-nowrap">
                        {s.version}
                      </td>
                      <td className="px-5 py-4 text-gray-600 align-top max-w-md">
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

      {/* Status legend explanation */}
      <div className="mt-12 rounded-xl border border-gray-100 bg-gray-50 px-6 py-5">
        <h2 className="mb-3 text-sm font-semibold text-gray-700">Status definitions</h2>
        <dl className="space-y-2 text-sm">
          <div className="flex items-start gap-3">
            <StatusBadge status="compliant" />
            <dd className="text-gray-600">
              Implemented and verified in code. Automated or manual tests confirm the behaviour.
            </dd>
          </div>
          <div className="flex items-start gap-3">
            <StatusBadge status="targeted" />
            <dd className="text-gray-600">
              Actively targeted. Core infrastructure is in place; automated coverage is being
              expanded across all pages and flows.
            </dd>
          </div>
          <div className="flex items-start gap-3">
            <StatusBadge status="partial" />
            <dd className="text-gray-600">
              Partially implemented. Some flows are covered; remaining gaps are tracked and
              scheduled.
            </dd>
          </div>
        </dl>
      </div>

      {/* Build stamp footer */}
      <p className="mt-8 text-center text-xs text-gray-400">
        This page is generated at build time.{" "}
        {BUILD_TIME && (
          <>
            Last deployment:{" "}
            <time dateTime={BUILD_TIME}>{formatBuildTime(BUILD_TIME)}</time>.
          </>
        )}{" "}
        Standards data is sourced from{" "}
        <code className="rounded bg-gray-100 px-1 py-0.5">web/lib/compliance.ts</code>.
      </p>
    </div>
  );
}
