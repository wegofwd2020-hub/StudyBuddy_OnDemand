"use client";

/**
 * Tour-B — Teacher capability tour (Layer 0, pre-auth)
 *
 * Six-step linear walkthrough of everything a teacher can do in the school
 * portal. No JWT, no API calls — pure static content.
 * Ends with a login CTA (teachers are provisioned by their School Admin,
 * not self-registered).
 *
 * Content sourced from: studybuddy-docs/help/overview/teacher.html
 *                       studybuddy-docs/help/help/teacher/
 * SVG flows reused from: public/assets/tour/ (same set as Tour-A)
 * Accent colour: blue-600 (matches teacher role card on /tour)
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
    title: "Your role as a teacher",
    outcome:
      "You manage classrooms, assign curriculum, and track your students' progress. Your School Admin handles school-wide setup — you focus on teaching.",
    detail: (
      <>
        <p className="mb-4 text-sm leading-relaxed text-gray-600">
          As a teacher in the school portal you have access to everything needed
          to run a personalised, self-paced learning experience for your students:
        </p>
        <div className="overflow-hidden rounded-lg border">
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                  You can
                </th>
                <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                  Your School Admin handles
                </th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {[
                ["Create and manage classrooms", "Provisioning teacher accounts"],
                ["Assign curriculum packages to classrooms", "Provisioning student accounts"],
                ["Enrol students in classrooms", "School subscription and billing"],
                ["Track per-student progress and quiz scores", "Approving curriculum builds"],
                ["Act on at-risk student alerts", "School-wide settings"],
                ["Download CSV reports", "Promoting teachers to admin"],
              ].map(([can, admin]) => (
                <tr key={can} className="bg-white">
                  <td className="px-4 py-2.5 text-gray-800">{can}</td>
                  <td className="px-4 py-2.5 text-gray-400">{admin}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </>
    ),
  },
  {
    title: "Your first login",
    outcome:
      "Your School Admin provisions your account and emails you a temporary password. You must set a permanent password before accessing any portal page.",
    detail:
      "When you log in for the first time the portal immediately redirects you to a Change Password screen. " +
      "You cannot navigate to classrooms, reports, or any other page until you set a permanent password " +
      "(minimum 12 characters). This is enforced at the portal layout level — not just on the login page. " +
      "After setting your permanent password you land on the school dashboard and see your assigned " +
      "students and classrooms. If you ever forget your password, the Forgot password link on the login " +
      "page sends a reset link to your email — you do not need to contact your admin.",
    svgSrc: "/assets/tour/first-login-flow.svg",
    svgAlt: "Temporary password → forced reset → portal access",
    svgHeight: 400,
  },
  {
    title: "Create classrooms & assign curriculum",
    outcome:
      "A classroom links students to curriculum content. Create one per class section, assign packages from the catalog, then enrol students.",
    detail: (
      <>
        <p className="mb-3 text-sm leading-relaxed text-gray-600">
          The classroom is the central unit of content delivery. You can have as
          many classrooms as you need. Here's the lifecycle of a classroom:
        </p>
        <ol className="mb-4 space-y-2 pl-5 text-sm text-gray-600" style={{ listStyleType: "decimal" }}>
          <li>
            Go to <strong>Classrooms → Create classroom</strong>. Enter a name (e.g.{" "}
            <em>Grade 8 — Section A</em>) and an optional grade.
          </li>
          <li>
            Click <strong>Assign package</strong>. Browse the catalog — platform
            packages and your school's own custom packages are both listed. Assign
            one or more.
          </li>
          <li>
            Reorder packages using the drag handles. Students work through them
            in that order.
          </li>
          <li>
            Go to the <strong>Students</strong> tab and enrol your students. Once
            enrolled, they immediately gain access to all assigned packages.
          </li>
        </ol>
        <p className="text-sm text-gray-500">
          A classroom with no packages shows no content to students — always
          assign at least one package before enrolling.
        </p>
      </>
    ),
  },
  {
    title: "Enrol your students",
    outcome:
      "Your School Admin assigns students to your roster. You then enrol them in classrooms — each enrolment gives the student access to that classroom's curriculum.",
    detail:
      "You can only enrol students who are already assigned to you by your School Admin. " +
      "A student can be enrolled in more than one classroom — useful for cross-subject groups. " +
      "Removing a student from a classroom revokes their content access but preserves their " +
      "progress data. If you re-enrol them later, their history is intact. " +
      "If a student you expect is not in the search results when enrolling, ask your School Admin " +
      "to assign that student to you via Students → the student's name → Assignment.",
    svgSrc: "/assets/tour/student-enrolment-flow.svg",
    svgAlt: "Student provisioned by admin → assigned to teacher → enrolled in classroom → accesses content",
    svgHeight: 480,
  },
  {
    title: "Track student progress",
    outcome:
      "The Reports section shows completion rates, quiz averages, streaks, and last-active dates for every student assigned to you.",
    detail: (
      <>
        <p className="mb-4 text-sm leading-relaxed text-gray-600">
          StudyBuddy records every lesson view, quiz attempt, and session. You see
          reports scoped to your students only — not the whole school. Each metric
          is precisely defined so you can interpret it consistently:
        </p>
        <div className="overflow-hidden rounded-lg border">
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                  Metric
                </th>
                <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                  Definition
                </th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {[
                ["Completion rate", "% of units in assigned packages the student has opened at least once"],
                ["Quiz average", "Average of best score per quiz — only the best attempt per quiz counts"],
                ["Streak", "Consecutive calendar days with at least one lesson view or quiz answer"],
                ["Last active", "Most recent date of any recorded activity (lesson, quiz, or tutorial)"],
              ].map(([metric, def]) => (
                <tr key={metric} className="bg-white">
                  <td className="px-4 py-2.5 font-medium text-gray-800">{metric}</td>
                  <td className="px-4 py-2.5 text-gray-500">{def}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-3 text-sm text-gray-500">
          Click any student's name to see their full progress detail — unit by unit, quiz by quiz.
          All reports can be downloaded as CSV for your grade book or admin reports.
        </p>
      </>
    ),
  },
  {
    title: "At-risk alerts & reports",
    outcome:
      "Students inactive for 7+ consecutive days are automatically flagged at-risk. The At-risk report tells you exactly who to contact and how long they've been away.",
    detail: (
      <>
        <p className="mb-3 text-sm leading-relaxed text-gray-600">
          The at-risk flag is a soft alert — it does not block the student from studying.
          It is a signal for you to follow up. Once the student completes any lesson or
          quiz, the flag clears automatically.
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
                ["Overview", "Completion rate, quiz average, streak, last activity — one row per student"],
                ["At-risk", "Flagged students with days since last activity and their classroom"],
                ["Unit performance", "Average quiz score per unit — highlights units students find difficult"],
              ].map(([report, contents]) => (
                <tr key={report} className="bg-white">
                  <td className="px-4 py-2.5 font-medium text-gray-800">{report}</td>
                  <td className="px-4 py-2.5 text-gray-500">{contents}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-3 text-sm text-gray-500">
          Use the Unit performance report alongside the At-risk report: if a student
          stopped logging in right after a low quiz score, that unit is the likely barrier.
        </p>
      </>
    ),
  },
];

export default function TeacherTour() {
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
          <span className="text-sm font-medium text-blue-700">
            Teacher tour
          </span>
          <span className="text-sm text-gray-400">
            {current + 1} / {STEPS.length}
          </span>
        </div>
      </div>

      {/* Progress bar */}
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
                    ? "h-1.5 bg-blue-400"
                    : i === current
                    ? "h-2 bg-blue-600"
                    : "h-1.5 bg-gray-200"
                }`}
              />
            ))}
          </div>
          <div className="mt-2 flex items-center gap-1.5">
            {current > 0 && (
              <span className="flex items-center gap-1 text-xs text-blue-500">
                <CheckCircle2 className="h-3 w-3" />
                {current} of {STEPS.length} explored
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Personalised demo welcome banner (only when demo_token present) */}
      <DemoTourBanner token={demoToken} accentColor="blue" />

      {/* Step content */}
      <div className="mx-auto max-w-3xl px-6 py-10">
        <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-blue-500">
          Step {current + 1} of {STEPS.length}
        </p>

        <h1 className="mb-3 text-2xl font-bold text-gray-900 sm:text-3xl">
          {step.title}
        </h1>

        <p className="mb-6 text-base font-medium text-blue-700">
          {step.outcome}
        </p>

        <div className="mb-8">
          {typeof step.detail === "string" ? (
            <p className="text-sm leading-relaxed text-gray-600">{step.detail}</p>
          ) : (
            step.detail
          )}
        </div>

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
              className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-blue-700"
            >
              Next: {STEPS[current + 1].title}
              <ArrowRight className="h-4 w-4" />
            </button>
          </div>
        ) : (
          /* Final step CTA */
          <div className="rounded-xl border border-blue-200 bg-blue-50 p-6 text-center">
            <p className="mb-1 text-lg font-bold text-blue-900">
              Ready to log in?
            </p>
            <p className="mb-5 text-sm text-blue-700">
              Your School Admin has provisioned your account. Check your email
              for your temporary password and log in to get started.
            </p>
            <div className="flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
              <Link
                href="/school/login"
                className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-6 py-3 text-sm font-bold text-white shadow-sm hover:bg-blue-700"
              >
                Log in to school portal
                <ArrowRight className="h-4 w-4" />
              </Link>
              <button
                onClick={() => setCurrent((c) => c - 1)}
                className="flex items-center gap-1.5 text-sm text-blue-600 hover:underline"
              >
                <ArrowLeft className="h-4 w-4" />
                Review previous step
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Step index — quick jump */}
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
                    ? "border-blue-300 bg-blue-50 font-semibold text-blue-800"
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
