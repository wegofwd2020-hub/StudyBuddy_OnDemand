import type { Metadata } from "next";
import Link from "next/link";
import { School, GraduationCap, BookOpen, ArrowRight } from "lucide-react";

export const metadata: Metadata = {
  title: "Explore StudyBuddy OnDemand — Platform Tour",
  description:
    "Discover what StudyBuddy OnDemand can do for your school. Explore the platform from the perspective of a school admin, teacher, or student — before you register.",
};

const ROLES = [
  {
    icon: School,
    label: "School Admin",
    description:
      "Register your school, add teachers and students, build custom curricula, assign content to classrooms, and track progress school-wide.",
    cta: "Explore admin capabilities",
    href: "/tour/school-admin",
    available: true,
    accent: "violet",
  },
  {
    icon: GraduationCap,
    label: "Teacher",
    description:
      "Create classrooms, assign content packages, monitor student progress, flag at-risk learners, and download class reports.",
    cta: "Explore teacher capabilities",
    href: "/tour/teacher",
    available: false,
    accent: "blue",
  },
  {
    icon: BookOpen,
    label: "Student",
    description:
      "Access your personalised lessons, quizzes, and tutorials. Work through units at your own pace — even offline.",
    cta: "Explore student experience",
    href: "/tour/student",
    available: false,
    accent: "green",
  },
] as const;

const accentClasses = {
  violet: {
    border: "border-violet-200 hover:border-violet-400",
    icon: "bg-violet-100 text-violet-700",
    badge: "bg-violet-600",
    link: "bg-violet-600 hover:bg-violet-700 text-white",
    soon: "bg-violet-100 text-violet-600",
  },
  blue: {
    border: "border-blue-200 hover:border-blue-400",
    icon: "bg-blue-100 text-blue-700",
    badge: "bg-blue-600",
    link: "bg-blue-600 hover:bg-blue-700 text-white",
    soon: "bg-blue-100 text-blue-600",
  },
  green: {
    border: "border-green-200 hover:border-green-400",
    icon: "bg-green-100 text-green-700",
    badge: "bg-green-600",
    link: "bg-green-600 hover:bg-green-700 text-white",
    soon: "bg-green-100 text-green-600",
  },
} as const;

export default function TourPage() {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Hero */}
      <div className="border-b bg-white px-6 py-14 text-center">
        <p className="mb-2 text-sm font-semibold uppercase tracking-widest text-violet-600">
          No account needed
        </p>
        <h1 className="text-3xl font-bold text-gray-900 sm:text-4xl">
          Explore the platform
        </h1>
        <p className="mx-auto mt-4 max-w-xl text-base text-gray-500">
          Choose a role to see exactly what you can do with StudyBuddy OnDemand.
          Each tour walks through the key capabilities, step by step.
        </p>
      </div>

      {/* Role cards */}
      <div className="mx-auto max-w-4xl px-6 py-12">
        <div className="grid gap-6 md:grid-cols-3">
          {ROLES.map((role) => {
            const Icon = role.icon;
            const c = accentClasses[role.accent];
            return (
              <div
                key={role.label}
                className={`flex flex-col rounded-xl border bg-white p-6 shadow-sm transition-colors ${c.border}`}
              >
                <div className={`mb-4 inline-flex w-fit rounded-lg p-3 ${c.icon}`}>
                  <Icon className="h-6 w-6" />
                </div>
                <h2 className="mb-1 text-lg font-semibold text-gray-900">
                  {role.label}
                </h2>
                <p className="mb-6 flex-1 text-sm leading-relaxed text-gray-500">
                  {role.description}
                </p>
                {role.available ? (
                  <Link
                    href={role.href}
                    className={`inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold transition-colors ${c.link}`}
                  >
                    {role.cta}
                    <ArrowRight className="h-4 w-4" />
                  </Link>
                ) : (
                  <span
                    className={`inline-flex items-center justify-center rounded-lg px-4 py-2.5 text-sm font-semibold ${c.soon}`}
                  >
                    Coming soon
                  </span>
                )}
              </div>
            );
          })}
        </div>

        {/* Bottom nudge */}
        <p className="mt-10 text-center text-sm text-gray-400">
          Already have a school?{" "}
          <Link href="/school/login" className="text-violet-600 hover:underline">
            Log in to your school portal
          </Link>
        </p>
      </div>
    </div>
  );
}
