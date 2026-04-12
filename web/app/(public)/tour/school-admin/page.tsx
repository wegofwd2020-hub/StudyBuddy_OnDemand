"use client";

/**
 * Tour-A — School Admin capability tour (Layer 0, pre-auth)
 *
 * Six-step linear walkthrough of everything a school admin can do.
 * No JWT, no API calls — pure static content.
 * Ends with a registration CTA.
 *
 * Content sourced from: studybuddy-docs/help/overview/school-admin.html
 * SVG flows sourced from: studybuddy-docs/help/flows/  (copied to public/assets/tour/)
 */

import { useState } from "react";
import { useSearchParams } from "next/navigation";
import Image from "next/image";
import Link from "next/link";
import { ArrowLeft, ArrowRight, CheckCircle2 } from "lucide-react";
import { DemoTourBanner } from "@/components/demo/DemoTourBanner";

interface Step {
  title: string;
  outcome: string;
  detail: string | React.ReactNode;
  svgSrc?: string;
  svgAlt?: string;
  svgHeight?: number;
}

const STEPS: Step[] = [
  {
    title: "Register your school",
    outcome:
      "One sign-up gives your whole school access. No per-teacher or per-student account is needed to start.",
    detail:
      "When you register, you create a school record and become its first School Admin. " +
      "Your school gets a unique enrolment code that teachers and students use to associate " +
      "their accounts with your institution. You can add more admins later by promoting any " +
      "provisioned teacher. The entire process takes about two minutes.",
    svgSrc: "/assets/tour/school-registration-flow.svg",
    svgAlt: "School registration end-to-end sequence",
    svgHeight: 300,
  },
  {
    title: "Provision teachers",
    outcome:
      "Add your teaching staff by email. They receive a temporary password and are prompted to reset it on first login — no separate invite workflow.",
    detail:
      "Provisioned teachers belong exclusively to your school. You set their name and email; " +
      "the system generates a secure temporary password and emails it to them. On first login " +
      "they are required to set a permanent password before accessing any portal pages. " +
      "You can assign teachers to specific grades and promote any teacher to School Admin.",
    svgSrc: "/assets/tour/first-login-flow.svg",
    svgAlt: "First-login forced password reset flow",
    svgHeight: 400,
  },
  {
    title: "Enrol students",
    outcome:
      "Upload a roster or add students individually by email and grade. Assign each student to a teacher and classroom.",
    detail:
      "Students are provisioned the same way as teachers — you provide the email and grade, " +
      "the system generates a temporary password and emails it. Students are then assigned " +
      "to a teacher and a grade. Enrolment in a classroom determines which curriculum content " +
      "they see. A student can only be enrolled in one school at a time.",
    svgSrc: "/assets/tour/student-enrolment-flow.svg",
    svgAlt: "Student provisioning to classroom to content access",
    svgHeight: 480,
  },
  {
    title: "Build a custom curriculum",
    outcome:
      "Define subjects and units, submit for review, then trigger an AI-generated content build — lessons, quizzes, tutorials, and audio — in any supported language.",
    detail: (
      <>
        <p className="mb-3 text-sm leading-relaxed text-gray-600">
          StudyBuddy provides a growing catalog of pre-built platform curriculum
          packages. If your school needs custom content — a specific syllabus, regional
          requirements, or a language not yet in the catalog — you can define and build
          it yourself:
        </p>
        <ol className="mb-3 space-y-1.5 pl-5 text-sm text-gray-600" style={{ listStyleType: "decimal" }}>
          <li>Submit a <strong>Curriculum Definition</strong> — a structured list of subjects and units.</li>
          <li>A platform reviewer approves the definition (typically within 24 hours).</li>
          <li>You trigger the AI content build. A cost estimate is shown before you confirm.</li>
          <li>The pipeline generates content in the background (15–60 minutes per grade).</li>
          <li>The finished curriculum package appears in your catalog, ready to assign.</li>
        </ol>
        <p className="text-sm text-gray-500">
          Build costs depend on your subscription plan. Starter plans include a fixed
          number of builds per month.
        </p>
      </>
    ),
    svgSrc: "/assets/tour/curriculum-lifecycle-flow.svg",
    svgAlt: "Curriculum definition to approval to build to classroom assignment",
    svgHeight: 540,
  },
  {
    title: "Assign content to classrooms",
    outcome:
      "Attach curriculum packages to classrooms. Students see only the content assigned to their classroom — nothing else.",
    detail: (
      <>
        <p className="mb-4 text-sm leading-relaxed text-gray-600">
          A classroom is the unit of content delivery. Each classroom has an optional
          grade and teacher. You assign one or more curriculum packages to a classroom;
          the packages are ordered and presented to students in that order. Platform
          packages (pre-built) and your own school-built packages can be mixed freely.
        </p>
        <div className="overflow-hidden rounded-lg border">
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                  Action
                </th>
                <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                  Result
                </th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {[
                ["Create a classroom", "An empty container with a name, optional grade and teacher"],
                ["Assign a curriculum package", "Students in the classroom can access that package's content"],
                ["Reorder packages", "Controls the sequence students work through content"],
                ["Enrol a student", "Student gains access to all packages assigned to the classroom"],
                ["Archive a classroom", "Classroom hidden from active views; data preserved"],
              ].map(([action, result]) => (
                <tr key={action} className="bg-white">
                  <td className="px-4 py-2.5 font-medium text-gray-800">{action}</td>
                  <td className="px-4 py-2.5 text-gray-500">{result}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </>
    ),
  },
  {
    title: "Track progress and at-risk students",
    outcome:
      "Per-student completion rates, quiz scores, and an at-risk flag for students falling behind — visible to both admins and teachers.",
    detail: (
      <>
        <p className="mb-4 text-sm leading-relaxed text-gray-600">
          StudyBuddy tracks every lesson view, quiz attempt, and session duration for
          each student. School Admins see aggregate metrics across the whole school.
          Teachers see metrics for their assigned students. An "at-risk" flag is raised
          automatically when a student's activity falls below their class average for
          seven consecutive days. Admins can download class-level and school-level
          reports as CSV.
        </p>
        <div className="overflow-hidden rounded-lg border">
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                  Report
                </th>
                <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                  Contents
                </th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {[
                ["Class overview", "Completion rate, quiz average, streak, last activity — per student"],
                ["At-risk students", "Students flagged as at-risk with days since last activity"],
                ["Unit performance", "Average quiz score per unit across all students in a class"],
                ["School summary", "Aggregated metrics across all classrooms"],
              ].map(([report, contents]) => (
                <tr key={report} className="bg-white">
                  <td className="px-4 py-2.5 font-medium text-gray-800">{report}</td>
                  <td className="px-4 py-2.5 text-gray-500">{contents}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </>
    ),
  },
];

export default function SchoolAdminTour() {
  const [current, setCurrent] = useState(0);
  const searchParams = useSearchParams();
  const demoToken = searchParams.get("demo_token");
  const step = STEPS[current];
  const isFirst = current === 0;
  const isLast = current === STEPS.length - 1;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Top bar */}
      <div className="border-b bg-white px-6 py-4">
        <div className="mx-auto flex max-w-3xl items-center justify-between gap-4">
          <Link
            href="/tour"
            className="flex items-center gap-1.5 text-sm text-gray-400 hover:text-gray-700"
          >
            <ArrowLeft className="h-4 w-4" />
            All roles
          </Link>
          <span className="text-sm font-medium text-violet-700">
            School Admin tour
          </span>
          <span className="text-sm text-gray-400">
            {current + 1} / {STEPS.length}
          </span>
        </div>
      </div>

      {/* Progress dots */}
      <div className="border-b bg-white px-6 pb-4">
        <div className="mx-auto max-w-3xl">
          <div className="flex items-center gap-2 pt-3">
            {STEPS.map((s, i) => (
              <button
                key={i}
                onClick={() => setCurrent(i)}
                aria-label={`Go to step ${i + 1}: ${s.title}`}
                className={`flex-1 rounded-full transition-all ${
                  i < current
                    ? "h-1.5 bg-violet-400"
                    : i === current
                    ? "h-2 bg-violet-600"
                    : "h-1.5 bg-gray-200"
                }`}
              />
            ))}
          </div>
          <div className="mt-2 flex items-center gap-1.5">
            {current > 0 && (
              <span className="flex items-center gap-1 text-xs text-violet-500">
                <CheckCircle2 className="h-3 w-3" />
                {current} of {STEPS.length} explored
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Personalised demo welcome banner (only when demo_token present) */}
      <DemoTourBanner token={demoToken} accentColor="violet" />

      {/* Step content */}
      <div className="mx-auto max-w-3xl px-6 py-10">
        {/* Step label */}
        <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-violet-500">
          Step {current + 1} of {STEPS.length}
        </p>

        {/* Title */}
        <h1 className="mb-3 text-2xl font-bold text-gray-900 sm:text-3xl">
          {step.title}
        </h1>

        {/* Outcome — the "why it matters" sentence */}
        <p className="mb-6 text-base font-medium text-violet-700">
          {step.outcome}
        </p>

        {/* Detail */}
        <div className="mb-8">
          {typeof step.detail === "string" ? (
            <p className="text-sm leading-relaxed text-gray-600">{step.detail}</p>
          ) : (
            step.detail
          )}
        </div>

        {/* SVG flow diagram */}
        {step.svgSrc && (
          <figure className="mb-8 overflow-hidden rounded-xl border bg-white p-4 shadow-sm">
            <Image
              src={step.svgSrc}
              alt={step.svgAlt ?? ""}
              width={720}
              height={step.svgHeight ?? 400}
              className="mx-auto"
              unoptimized
            />
            <figcaption className="mt-2 text-center text-xs text-gray-400">
              {step.svgAlt}
            </figcaption>
          </figure>
        )}

        {/* Navigation */}
        {!isLast ? (
          <div className="flex items-center gap-3">
            {!isFirst && (
              <button
                onClick={() => setCurrent((c) => c - 1)}
                className="flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-5 py-2.5 text-sm font-medium text-gray-600 shadow-sm hover:bg-gray-50"
              >
                <ArrowLeft className="h-4 w-4" />
                Back
              </button>
            )}
            <button
              onClick={() => setCurrent((c) => c + 1)}
              className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-violet-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-violet-700"
            >
              Next: {STEPS[current + 1].title}
              <ArrowRight className="h-4 w-4" />
            </button>
          </div>
        ) : (
          /* Final step CTA */
          <div className="rounded-xl border border-violet-200 bg-violet-50 p-6 text-center">
            <p className="mb-1 text-lg font-bold text-violet-900">
              Ready to get started?
            </p>
            <p className="mb-5 text-sm text-violet-700">
              Register your school in about two minutes. No credit card required to start.
            </p>
            <div className="flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
              <Link
                href="/school/register"
                className="inline-flex items-center gap-2 rounded-lg bg-violet-600 px-6 py-3 text-sm font-bold text-white shadow-sm hover:bg-violet-700"
              >
                Register your school
                <ArrowRight className="h-4 w-4" />
              </Link>
              <button
                onClick={() => setCurrent((c) => c - 1)}
                className="flex items-center gap-1.5 text-sm text-violet-600 hover:underline"
              >
                <ArrowLeft className="h-4 w-4" />
                Review previous step
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Step index — quick jump on desktop */}
      <div className="border-t bg-white py-6">
        <div className="mx-auto max-w-3xl px-6">
          <p className="mb-3 text-xs font-semibold uppercase tracking-widest text-gray-400">
            All capabilities
          </p>
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {STEPS.map((s, i) => (
              <button
                key={i}
                onClick={() => setCurrent(i)}
                className={`rounded-lg border px-3 py-2 text-left text-sm transition-colors ${
                  i === current
                    ? "border-violet-300 bg-violet-50 font-semibold text-violet-800"
                    : i < current
                    ? "border-gray-200 bg-gray-50 text-gray-500"
                    : "border-gray-200 bg-white text-gray-600 hover:border-gray-300 hover:bg-gray-50"
                }`}
              >
                <span className="mr-1.5 text-xs text-gray-400">{i + 1}.</span>
                {s.title}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
