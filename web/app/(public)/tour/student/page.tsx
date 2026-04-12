"use client";

/**
 * Tour-C — Student experience tour (Layer 0, pre-auth)
 *
 * Five-step linear walkthrough of what a student can do in the portal.
 * No JWT, no API calls — pure static content.
 * Ends with a "contact your school" CTA — students cannot self-register,
 * their accounts are provisioned by their School Admin.
 *
 * Content sourced from: studybuddy-docs/help/overview/student.html
 *                       studybuddy-docs/help/help/student/
 * SVG flows reused from: public/assets/tour/
 * Accent colour: green-600 (matches student role card on /tour)
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
    title: "Receive your school login",
    outcome:
      "Your School Admin creates your account and emails you a temporary password. You set a permanent password on your first login — no admin involvement needed after that.",
    detail: (
      <>
        <p className="mb-3 text-sm leading-relaxed text-gray-600">
          You don't sign up for StudyBuddy — your school does. Here's how your
          account reaches you:
        </p>
        <ol
          className="mb-4 space-y-2 pl-5 text-sm text-gray-600"
          style={{ listStyleType: "decimal" }}
        >
          <li>
            Your School Admin provisions your account and the system sends you a
            welcome email with a temporary password.
          </li>
          <li>
            Open the link in the email and enter your school email address and
            the temporary password.
          </li>
          <li>
            You are immediately taken to a{" "}
            <strong>Change Password screen</strong>. Enter a new permanent
            password (at least 12 characters) and confirm it.
          </li>
          <li>
            Click <strong>Save password</strong> — you land on the student
            dashboard and your content is ready.
          </li>
        </ol>
        <p className="text-sm text-gray-500">
          You cannot skip the Change Password screen. All portal pages redirect
          back to it until it is complete. If you later forget your password,
          the Forgot password link on the login page sends a reset link to your
          school email — no need to contact anyone.
        </p>
      </>
    ),
    svgSrc: "/assets/tour/first-login-flow.svg",
    svgAlt: "Temporary password → forced reset → student dashboard",
    svgHeight: 400,
  },
  {
    title: "Access your personalised lessons",
    outcome:
      "Your home screen shows every subject your teacher has assigned to your classroom. Each subject contains units with lessons, quizzes, and tutorials — all matched to your grade level.",
    detail: (
      <>
        <p className="mb-3 text-sm leading-relaxed text-gray-600">
          The content you see is determined entirely by your classroom
          enrolment. Your teacher assigns curriculum packages to your
          classroom — you see exactly those subjects, nothing more and nothing
          less.
        </p>
        <div className="overflow-hidden rounded-lg border">
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                  Content type
                </th>
                <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                  What it is
                </th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {[
                ["Lesson", "Text + diagrams explaining the topic. Saves your place automatically."],
                ["Audio", "A spoken reading of the lesson — tap play and listen instead of reading."],
                ["Quiz", "Questions on the lesson content. Instant results, unlimited retakes."],
                ["Tutorial", "Step-by-step worked examples with guided exercises."],
                ["Experiment", "Interactive lab steps for science units (where applicable)."],
              ].map(([type, desc]) => (
                <tr key={type} className="bg-white">
                  <td className="px-4 py-2.5 font-medium text-gray-800">{type}</td>
                  <td className="px-4 py-2.5 text-gray-500">{desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-3 text-sm text-gray-500">
          If your home screen is empty or shows "No content available", your
          teacher may not have assigned a curriculum package yet — contact them.
        </p>
      </>
    ),
  },
  {
    title: "Work through units at your own pace",
    outcome:
      "You decide when and how fast you study. Progress saves automatically — you can stop mid-lesson and pick up exactly where you left off.",
    detail: (
      <>
        <p className="mb-3 text-sm leading-relaxed text-gray-600">
          Each subject is made up of units. Open any unit to see its lesson,
          quiz, and tutorial. There is no fixed schedule inside a unit —
          read the lesson, listen to the audio, do the quiz in any order that
          works for you.
        </p>
        <ol
          className="mb-4 space-y-2 pl-5 text-sm text-gray-600"
          style={{ listStyleType: "decimal" }}
        >
          <li>
            From the home screen, click a <strong>subject card</strong> (e.g.
            Mathematics, Physical Science).
          </li>
          <li>Click a unit name to open it.</li>
          <li>
            Use the tabs — <strong>Lesson</strong>, <strong>Quiz</strong>,{" "}
            <strong>Tutorial</strong> — to switch between content types.
          </li>
          <li>
            Scroll through the lesson. Your progress saves as you go — no save
            button.
          </li>
          <li>
            Close the app or browser at any time. When you return, the lesson
            opens where you left off.
          </li>
        </ol>
        <p className="text-sm text-gray-500">
          Your lesson view is recorded the moment you open a unit. This
          contributes to your completion rate and keeps your study streak alive.
        </p>
      </>
    ),
  },
  {
    title: "Take quizzes and get instant feedback",
    outcome:
      "Every unit has one or more quizzes. Submit your answers and see your score and the correct answers immediately. Retake as many times as you like — only your best score is recorded.",
    detail: (
      <>
        <p className="mb-4 text-sm leading-relaxed text-gray-600">
          Quizzes are designed to help you learn, not just test you. You get the
          correct answer and an explanation for every question you got wrong, so
          each attempt builds on the last.
        </p>
        <div className="overflow-hidden rounded-lg border">
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                  How it works
                </th>
                <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                  Detail
                </th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {[
                ["Attempts", "Unlimited — retake any quiz as many times as you like."],
                ["Scoring", "Each attempt is scored separately. Only your best score is kept."],
                ["Results", "Shown immediately after submit — correct answers + explanations for wrong answers."],
                ["Teacher view", "Your teacher sees your best score per quiz, not individual attempts."],
                ["Sequence", "Questions may appear in a different order on each retake."],
              ].map(([how, detail]) => (
                <tr key={how} className="bg-white">
                  <td className="px-4 py-2.5 font-medium text-gray-800">{how}</td>
                  <td className="px-4 py-2.5 text-gray-500">{detail}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </>
    ),
  },
  {
    title: "Track your progress and streaks",
    outcome:
      "The progress section shows your completion rate, quiz average, and how many consecutive days you've studied. Your teacher can see these numbers and uses them to check in if you've been inactive.",
    detail: (
      <>
        <p className="mb-4 text-sm leading-relaxed text-gray-600">
          Every lesson view, quiz attempt, and tutorial session is recorded.
          Here is what each metric means:
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
                ["Completion rate", "% of units you've opened at least once across all assigned packages."],
                ["Quiz average", "Average of your best score per quiz, across all quizzes."],
                ["Streak", "Consecutive days with any activity — lesson, quiz, or tutorial. Resets if a full day passes with nothing."],
                ["Last active", "The most recent date you did anything in the portal."],
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
          If you haven't been active for 7 or more days, your teacher sees an
          at-risk flag next to your name. It clears automatically the moment you
          study again — no action needed on your part.
        </p>
      </>
    ),
  },
];

export default function StudentTour() {
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
          <span className="text-sm font-medium text-green-700">
            Student tour
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
                    ? "h-1.5 bg-green-400"
                    : i === current
                    ? "h-2 bg-green-600"
                    : "h-1.5 bg-gray-200"
                }`}
              />
            ))}
          </div>
          <div className="mt-2 flex items-center gap-1.5">
            {current > 0 && (
              <span className="flex items-center gap-1 text-xs text-green-500">
                <CheckCircle2 className="h-3 w-3" />
                {current} of {STEPS.length} explored
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Personalised demo welcome banner (only when demo_token present) */}
      <DemoTourBanner token={demoToken} accentColor="green" />

      {/* Step content */}
      <div className="mx-auto max-w-3xl px-6 py-10">
        <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-green-500">
          Step {current + 1} of {STEPS.length}
        </p>

        <h1 className="mb-3 text-2xl font-bold text-gray-900 sm:text-3xl">
          {step.title}
        </h1>

        <p className="mb-6 text-base font-medium text-green-700">
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
              className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-green-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-green-700"
            >
              Next: {STEPS[current + 1].title}
              <ArrowRight className="h-4 w-4" />
            </button>
          </div>
        ) : (
          /* Final step CTA — students cannot self-register */
          <div className="rounded-xl border border-green-200 bg-green-50 p-6 text-center">
            <p className="mb-1 text-lg font-bold text-green-900">
              Ready to get started?
            </p>
            <p className="mb-5 text-sm text-green-700">
              Student accounts are set up by your school. Ask your teacher or
              School Admin for your login details — they'll send you an email
              with your temporary password.
            </p>
            <div className="flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
              <Link
                href="/tour/school-admin"
                className="inline-flex items-center gap-2 rounded-lg bg-green-600 px-6 py-3 text-sm font-bold text-white shadow-sm hover:bg-green-700"
              >
                Are you a School Admin?
                <ArrowRight className="h-4 w-4" />
              </Link>
              <Link
                href="/tour/teacher"
                className="inline-flex items-center gap-2 rounded-lg border border-green-300 bg-white px-6 py-3 text-sm font-semibold text-green-700 shadow-sm hover:bg-green-50"
              >
                Are you a Teacher?
                <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
            <button
              onClick={() => setCurrent((c) => c - 1)}
              className="mt-4 flex items-center gap-1.5 text-sm text-green-600 hover:underline mx-auto"
            >
              <ArrowLeft className="h-4 w-4" />
              Review previous step
            </button>
          </div>
        )}
      </div>

      {/* Step index — quick jump */}
      <div className="border-t bg-white py-6">
        <div className="mx-auto max-w-3xl px-6">
          <p className="mb-3 text-xs font-semibold uppercase tracking-widest text-gray-400">
            All steps
          </p>
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {STEPS.map((s, i) => (
              <button
                key={i}
                onClick={() => setCurrent(i)}
                className={`rounded-lg border px-3 py-2 text-left text-sm transition-colors ${
                  i === current
                    ? "border-green-300 bg-green-50 font-semibold text-green-800"
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
