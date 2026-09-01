"use client";

import { useState } from "react";
import { MindMap } from "@/components/help/MindMap";
import { HELP_MINDMAPS } from "@/lib/content/help-mindmaps";
import { useDemoStudent } from "@/lib/hooks/useDemoStudent";
import { HelpCircle, ChevronDown, ChevronUp } from "lucide-react";
import { cn } from "@/lib/utils";

const GETTING_STARTED_DEMO = [
  {
    step: "1",
    title: "Request access",
    body: 'Click "Try it free" on the homepage, enter your email, and submit the request form. Check your inbox for the magic link.',
  },
  {
    step: "2",
    title: "Log in",
    body: "Open the magic link, then log in with your email and password at /demo/login. You get Grade 8 content automatically.",
  },
  {
    step: "3",
    title: "Explore subjects",
    body: "Go to Subjects or the Curriculum Map to browse your assigned subject units.",
  },
  {
    step: "4",
    title: "Start a unit — lesson first",
    body: "Click any unit to open its Lesson, Tutorial, Quiz, and Activity. Read the lesson before the quiz: the quiz stays locked until you've opened it. Quizzes give immediate feedback.",
  },
  {
    step: "5",
    title: "Track your progress",
    body: "Check Progress for your unit history and quiz scores. My Stats shows totals across subjects.",
  },
];

const GETTING_STARTED_FULL = [
  {
    step: "1",
    title: "Log in",
    body: "Sign in via your school enrolment code or your personal subscription. Your grade and curriculum are set automatically.",
  },
  {
    step: "2",
    title: "Dashboard",
    body: "See your daily streak, recently viewed units, and a quick summary of quiz scores.",
  },
  {
    step: "3",
    title: "Browse content",
    body: "Go to Subjects or Curriculum Map. Your school may have custom content — it shows alongside the default platform library.",
  },
  {
    step: "4",
    title: "Learning flow — lesson before quiz",
    body: "Each unit has a Lesson (with optional audio), a Tutorial (tabbed deep-dive), up to 3 Quiz sets, and an Activity where available. Open the lesson first — the quiz unlocks once you have. If you've already attempted a unit before, you can go straight back to its quiz.",
  },
  {
    step: "5",
    title: "Tell us what helped",
    body: "Lessons, tutorials and activities each have a thumbs up / thumbs down. A thumbs-down opens an optional comment box. Your teacher sees this, so it's the fastest way to flag something confusing or wrong.",
  },
  {
    step: "6",
    title: "Progress & Stats",
    body: "Progress shows your attempt history; My Stats shows totals, streaks, and a subject breakdown. Pass rate there counts every try — retaking a quiz and passing counts as a pass.",
  },
  {
    step: "7",
    title: "Settings",
    body: "Update display name, language (English/French/Spanish), notification preferences, and accessibility options.",
  },
];

// Short, and only questions a student actually arrives with. The first one is
// the single most likely support question after the lesson-before-quiz rule
// shipped (2026-09-01): a locked quiz looks like a fault unless something says
// otherwise.
const STUDENT_FAQ: { q: string; a: string }[] = [
  {
    q: "Why can't I start the quiz?",
    a: "Quizzes open once you've opened that unit's lesson. Tap 'Go to the lesson' on the message, have a read, and the quiz will be waiting when you come back. If you've taken that quiz before, it stays open — this only applies the first time.",
  },
  {
    q: "I retook a quiz. Which score counts?",
    a: "Your best score is the one shown against the unit. My Stats counts every attempt, so improving on a retake improves your figures. Your teacher also sees how you did on the first try, which is why their number can differ from yours.",
  },
  {
    q: "I forgot my password.",
    a: "Use 'Forgot password' on the sign-in page. The link we email lasts one hour and works once — if it's expired, just request another.",
  },
  {
    q: "Something in a lesson looks wrong.",
    a: "Use the thumbs-down at the bottom of the lesson and say what you noticed. It goes to your teacher.",
  },
];

export default function StudentHelpPage() {
  const demo = useDemoStudent();

  const personaId = demo ? "demo-student" : "full-student";
  const map = HELP_MINDMAPS.find((m) => m.id === personaId);
  const steps = demo ? GETTING_STARTED_DEMO : GETTING_STARTED_FULL;

  const [expanded, setExpanded] = useState<string | null>(personaId);

  return (
    <div className="max-w-5xl space-y-8 p-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <HelpCircle className="h-7 w-7 text-blue-600" />
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Help &amp; Tutorial</h1>
          <p className="text-sm text-gray-500">
            {demo
              ? "Demo account guide — explore Grade 8 content, no sign-up required."
              : "Student guide — your full learning experience."}
          </p>
        </div>
      </div>

      {/* Getting started */}
      <section>
        <h2 className="mb-4 text-sm font-semibold tracking-wide text-gray-500 uppercase">
          Getting Started
        </h2>
        <ol className="space-y-3">
          {steps.map((s) => (
            <li
              key={s.step}
              className="flex gap-4 rounded-lg border border-gray-100 bg-white p-4 shadow-sm"
            >
              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-blue-600 text-xs font-bold text-white">
                {s.step}
              </span>
              <div>
                <p className="font-medium text-gray-900">{s.title}</p>
                <p className="mt-0.5 text-sm text-gray-500">{s.body}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      {/* Mind map */}
      {map && (
        <section>
          <h2 className="mb-4 text-sm font-semibold tracking-wide text-gray-500 uppercase">
            Your Role — Mind Map
          </h2>
          <div className="overflow-hidden rounded-xl border border-gray-200 shadow-sm">
            <button
              className={cn(
                "flex w-full items-center justify-between px-5 py-4 text-left transition-colors",
                map.color,
              )}
              onClick={() => setExpanded(expanded === map.id ? null : map.id)}
              aria-expanded={expanded === map.id}
            >
              <div>
                <p className="font-semibold text-white">{map.title}</p>
                <p className="text-sm text-white/70">{map.subtitle}</p>
              </div>
              {expanded === map.id ? (
                <ChevronUp className="h-5 w-5 shrink-0 text-white" />
              ) : (
                <ChevronDown className="h-5 w-5 shrink-0 text-white" />
              )}
            </button>

            {expanded === map.id && (
              <div className="bg-white p-4">
                <MindMap diagram={map.diagram} className="min-h-[400px]" />
              </div>
            )}
          </div>
        </section>
      )}

      {/* Common questions */}
      <section>
        <h2 className="mb-4 text-sm font-semibold tracking-wide text-gray-500 uppercase">
          Common Questions
        </h2>
        <div className="space-y-2">
          {STUDENT_FAQ.map(({ q, a }) => (
            <details
              key={q}
              className="group rounded-lg border border-gray-100 bg-white shadow-sm"
            >
              <summary className="flex cursor-pointer items-center justify-between gap-3 px-4 py-3 font-medium text-gray-900 marker:content-none">
                {q}
                <ChevronDown className="h-4 w-4 shrink-0 text-gray-400 transition-transform group-open:rotate-180" />
              </summary>
              <div className="border-t border-gray-50 px-4 py-3">
                <p className="text-sm text-gray-600">{a}</p>
              </div>
            </details>
          ))}
        </div>
      </section>

      {/* Quick reference */}
      <section>
        <h2 className="mb-4 text-sm font-semibold tracking-wide text-gray-500 uppercase">
          Quick Reference
        </h2>
        <div className="overflow-hidden rounded-xl border border-gray-200 shadow-sm">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50">
                <th className="px-4 py-2 text-left font-medium text-gray-600">Task</th>
                <th className="px-4 py-2 text-left font-medium text-gray-600">Where</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {[
                ["Browse subjects", "/subjects"],
                ["Open Curriculum Map", "/curriculum"],
                ["Read a lesson", "/subjects → unit → Lesson tab"],
                ["Take a quiz (after the lesson)", "/subjects → unit → Quiz tab"],
                ["Say a lesson helped / didn't", "Thumbs at the foot of the lesson"],
                ["View quiz score history", "/progress"],
                ["See subject totals", "/stats"],
                ["Listen to a lesson (where available)", "Lesson page → audio player"],
                // The page has a Profile card alongside Language and Notifications, so the
                // old label undersold it and a student looking for their name or grade had
                // no signpost (Venki, 2026-08-28).
                !demo && [
                  "Update profile / language / notifications",
                  "/account/settings",
                ],
                ["Toggle dyslexia font", "Eye icon in top-right header, or Alt+D"],
                demo && [
                  "Demo limitations",
                  "Grade 8 only; audio download requires full account",
                ],
              ]
                .filter((r): r is string[] => Boolean(r))
                .map(([task, where]) => (
                  <tr key={task}>
                    <td className="px-4 py-2 text-gray-700">{task}</td>
                    <td className="px-4 py-2 font-mono text-xs text-blue-600">{where}</td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
