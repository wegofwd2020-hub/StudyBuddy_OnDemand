import type { Metadata } from "next";
import Link from "next/link";
import { LinkButton } from "@/components/ui/link-button";
import {
  ShieldCheck,
  FileCheck2,
  UserCheck,
  Lock,
  ScanText,
  Languages,
  Eye,
  BookOpenCheck,
} from "lucide-react";
import {
  COMPLIANCE_STANDARDS,
  COMPLIANCE_CATEGORIES,
  type ComplianceStatus,
} from "@/lib/compliance";

export const metadata: Metadata = {
  title: "Content Quality & Compliance",
  description:
    "Every StudyBuddy lesson passes the same gates before a student ever sees it — structure and language checks, a human review step, and privacy rules built into the platform. Here's exactly what those gates are.",
};

export default function QualityPage() {
  return (
    <>
      <HeroSection />
      <GatesSection />
      <StandardsSection />
      <AudienceSection />
      <CtaSection />
    </>
  );
}

// ── Hero ─────────────────────────────────────────────────────────────────────

function HeroSection() {
  return (
    <section className="bg-gradient-to-b from-blue-600 to-blue-700 px-4 py-20 text-center text-white">
      <div className="mx-auto max-w-3xl">
        <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
          Quality you can see. Compliance you can check.
        </h1>
        <p className="mt-6 text-xl text-blue-50">
          Every lesson, quiz, and activity passes the same set of gates before a student
          ever opens it. No piece of content reaches a child without clearing structure
          checks, a language scan, and a human review step.
        </p>
        <div className="mt-8 flex flex-wrap justify-center gap-4">
          <LinkButton href="/for-schools" size="lg" variant="secondary">
            StudyBuddy for schools
          </LinkButton>
          <LinkButton
            href="/about"
            size="lg"
            variant="outline"
            className="border-white/40 text-white hover:bg-white/10"
          >
            About us
          </LinkButton>
        </div>
      </div>
    </section>
  );
}

// ── The three-stage gate story ───────────────────────────────────────────────

const STAGES = [
  {
    n: "1",
    label: "Generated",
    title: "Built to a strict shape, then checked automatically",
    points: [
      {
        icon: FileCheck2,
        title: "Structure validation",
        body: "Every lesson, quiz, tutorial, and experiment must match a fixed structure before it is saved. Anything malformed is regenerated, never published. A quiz that isn't a complete set of well-formed questions simply does not ship.",
      },
      {
        icon: ScanText,
        title: "Inclusive-language scan",
        body: "All content is scanned for non-inclusive or insensitive language before it can be approved. Flagged passages must be cleared by a reviewer — they cannot be skipped.",
      },
      {
        icon: BookOpenCheck,
        title: "Age-appropriate & on-level",
        body: "Content is restricted to academic topics for Grades 5–12 and is generated to read 1–2 grade levels below the student's grade, so the focus stays on understanding.",
      },
    ],
  },
  {
    n: "2",
    label: "Reviewed",
    title: "A person approves it before any student sees it",
    points: [
      {
        icon: UserCheck,
        title: "Human approval gate",
        body: "Newly generated content starts as 'pending'. It only becomes visible to students after a reviewer explicitly approves and publishes it. Rejected or blocked content is held back, and any published version can be rolled back.",
      },
      {
        icon: Eye,
        title: "Side-by-side & annotated review",
        body: "Reviewers read the content unit by unit, leave notes against any section, and compare versions with word-level highlighting — so changes between revisions are never invisible.",
      },
      {
        icon: ScanText,
        title: "Warnings must be resolved",
        body: "Language-scan warnings are tracked individually. A version can't be approved until every warning is either fixed or explicitly marked as a reviewed false positive.",
      },
    ],
  },
  {
    n: "3",
    label: "Served safely",
    title: "Privacy and access rules are enforced by the platform",
    points: [
      {
        icon: Lock,
        title: "Records stay inside your school",
        body: "Progress, scores, and history are treated as educational records. Access is scoped to the student's own institution at the database level — one school can never see another's records.",
      },
      {
        icon: ShieldCheck,
        title: "Consent before access",
        body: "Students under 13 require verifiable parental consent before their account is activated. Until then, content access is blocked. We collect only the minimum information needed to run the service.",
      },
      {
        icon: Languages,
        title: "Built per language, not machine-translated",
        body: "English, French, and Spanish content is each generated and reviewed on its own. We don't run AI output through a translator and hope for the best.",
      },
    ],
  },
] as const;

function GatesSection() {
  return (
    <section className="bg-white px-4 py-20">
      <div className="mx-auto max-w-5xl">
        <div className="mx-auto max-w-3xl text-center">
          <h2 className="text-3xl font-bold text-gray-900">
            Three gates, every single time
          </h2>
          <p className="mt-4 text-gray-600">
            Content moves through these stages in order. A piece that fails any gate
            doesn&apos;t move forward — it&apos;s regenerated or held for a reviewer.
          </p>
        </div>

        <div className="mt-14 space-y-14">
          {STAGES.map(({ n, label, title, points }) => (
            <div key={n}>
              <div className="flex items-center gap-4">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-blue-600 text-sm font-bold text-white">
                  {n}
                </div>
                <div>
                  <p className="text-xs font-semibold tracking-wide text-blue-600 uppercase">
                    {label}
                  </p>
                  <h3 className="text-xl font-bold text-gray-900">{title}</h3>
                </div>
              </div>

              <div className="mt-6 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
                {points.map(({ icon: Icon, title: t, body }) => (
                  <div
                    key={t}
                    className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm"
                  >
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-50">
                      <Icon className="h-5 w-5 text-blue-600" />
                    </div>
                    <h4 className="mt-4 font-semibold text-gray-900">{t}</h4>
                    <p className="mt-2 text-sm text-gray-500">{body}</p>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ── Standards we hold ourselves to ───────────────────────────────────────────

const STATUS_META: Record<ComplianceStatus, { label: string; className: string }> = {
  compliant: { label: "Compliant", className: "bg-emerald-100 text-emerald-700" },
  targeted: { label: "Target", className: "bg-amber-100 text-amber-700" },
  partial: { label: "Partial", className: "bg-gray-100 text-gray-600" },
};

function StatusPill({ status }: { status: ComplianceStatus }) {
  const { label, className } = STATUS_META[status];
  return (
    <span
      className={`inline-flex shrink-0 items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${className}`}
    >
      {label}
    </span>
  );
}

function StandardsSection() {
  return (
    <section className="bg-gray-50 px-4 py-20">
      <div className="mx-auto max-w-5xl">
        <div className="mx-auto max-w-3xl text-center">
          <h2 className="text-3xl font-bold text-gray-900">
            The standards we hold ourselves to
          </h2>
          <p className="mt-4 text-gray-600">
            The full list of accessibility, privacy, security, and content standards we
            comply with or actively target. We label honestly:{" "}
            <span className="font-medium text-emerald-700">Compliant</span> means in place
            today; <span className="font-medium text-amber-700">Target</span> means we
            build to it and verify continuously, with an audit still in progress.
          </p>
        </div>

        <div className="mt-12 space-y-10">
          {COMPLIANCE_CATEGORIES.map((category) => {
            const items = COMPLIANCE_STANDARDS.filter((s) => s.category === category);
            if (items.length === 0) return null;
            return (
              <div key={category}>
                <h3 className="mb-4 text-sm font-semibold tracking-wide text-gray-500 uppercase">
                  {category}
                </h3>
                <div className="grid gap-4 sm:grid-cols-2">
                  {items.map((s) => (
                    <div
                      key={s.standard}
                      className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <h4 className="font-semibold text-gray-900">{s.standard}</h4>
                        <StatusPill status={s.status} />
                      </div>
                      <p className="mt-1 text-xs text-gray-400">{s.version}</p>
                      <p className="mt-3 text-sm text-gray-600">{s.description}</p>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>

        <p className="mt-10 text-center text-sm text-gray-500">
          Reviewing our setup for procurement?{" "}
          <Link href="/contact" className="font-medium text-blue-600 hover:underline">
            Ask us for the compliance one-pager →
          </Link>
        </p>
      </div>
    </section>
  );
}

// ── What this means for each audience ────────────────────────────────────────

const AUDIENCES = [
  {
    who: "For parents",
    body: "Your child sees academic content that an adult has reviewed and approved — not raw AI output. Under-13 accounts stay locked until you give consent, and we collect only name, email, grade, and language.",
  },
  {
    who: "For teachers",
    body: "What you assign has already cleared structure and language checks and a human approval step. You can customize and re-review your school's content, and nothing changes underneath students without a tracked version.",
  },
  {
    who: "For school & district admins",
    body: "Records never cross school boundaries, content carries an audit trail from generation to publish, and the standards above map cleanly onto FERPA, COPPA, and WCAG line items in your procurement checklist.",
  },
] as const;

function AudienceSection() {
  return (
    <section className="bg-white px-4 py-20">
      <div className="mx-auto max-w-5xl">
        <h2 className="text-center text-3xl font-bold text-gray-900">
          What this means for you
        </h2>
        <div className="mt-12 grid gap-6 md:grid-cols-3">
          {AUDIENCES.map(({ who, body }) => (
            <div key={who} className="rounded-2xl border border-blue-100 bg-blue-50 p-6">
              <h3 className="font-bold text-gray-900">{who}</h3>
              <p className="mt-2 text-sm text-gray-600">{body}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ── CTA ──────────────────────────────────────────────────────────────────────

function CtaSection() {
  return (
    <section className="bg-blue-600 px-4 py-20 text-center text-white">
      <div className="mx-auto max-w-2xl">
        <h2 className="text-3xl font-bold">Have a compliance question?</h2>
        <p className="mt-4 text-blue-50">
          We&apos;re happy to walk your team through any gate or standard on this page —
          and to share documentation for your procurement review.
        </p>
        <div className="mt-8 flex flex-wrap justify-center gap-4">
          <LinkButton href="/contact" size="lg" variant="secondary">
            Talk to us
          </LinkButton>
          <LinkButton
            href="/about"
            size="lg"
            variant="outline"
            className="border-white/40 text-white hover:bg-white/10"
          >
            More about StudyBuddy
          </LinkButton>
        </div>
      </div>
    </section>
  );
}
