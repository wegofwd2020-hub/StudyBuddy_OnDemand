import type { Metadata } from "next";
import { Check, Zap, School, Building2 } from "lucide-react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { LinkButton } from "@/components/ui/link-button";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";

export const metadata: Metadata = { title: "Pricing | StudyBuddy" };

const STARTER_FEATURES = [
  "Pre-built curricula for Grades 5–12",
  "Up to 30 students",
  "1 school admin + 2 teachers",
  "English content",
  "Standard school portal",
  "Student progress tracking",
];

const PRO_FEATURES = [
  "Everything in Platform Starter",
  "Unlimited students & teachers",
  "Custom curriculum builds (annual allowance included)",
  "English, French & Spanish content",
  "School branding & custom theme",
  "Classroom management",
  "Teacher analytics & reports",
  "Backup & restore",
];

const ENTERPRISE_FEATURES = [
  "Everything in School Pro",
  "Multi-school / district licensing",
  "Custom build quota",
  "Priority support & SLA",
  "Dedicated onboarding",
  "District admin dashboard",
  "SSO integration",
];

const FAQ = [
  {
    q: "What is included in the free Platform Starter plan?",
    a: "Platform Starter gives your school access to our pre-built STEM curricula for Grades 5–12 at no cost. You get up to 30 students, 2 teachers, and 1 school admin — no credit card required. Content is available in English.",
  },
  {
    q: "How does per-student pricing work for School Pro?",
    a: "School Pro is billed annually at roughly $5–8 per student per year — comparable to the cost of a single textbook. The exact price scales with your student count. Contact us for a precise quote.",
  },
  {
    q: "What counts as a custom curriculum build?",
    a: "A curriculum build is when StudyBuddy generates AI-powered lessons, quizzes, tutorials, and audio for a curriculum your school defines. School Pro includes an annual build allowance. Additional builds are available as paid add-ons.",
  },
  {
    q: "Can we keep using the platform if we exceed the Starter student limit?",
    a: "Yes — we will reach out before locking anything. Upgrading to School Pro unlocks unlimited students and teachers and takes effect immediately.",
  },
  {
    q: "What languages are supported?",
    a: "Pre-built content is available in English on the free Starter plan. School Pro and Enterprise unlock French and Spanish content. UI is available in all three languages on all plans.",
  },
  {
    q: "How does COPPA work for under-13 students?",
    a: "Schools create and manage student accounts, so the school acts as the consent authority for educational use — the route COPPA provides for schools. We collect only name, email, grade and language, and we do not track, profile or advertise to students. We do not run a separate parent-facing consent flow.",
  },
  {
    q: "How does Enterprise / district licensing work?",
    a: "Enterprise covers multiple schools under one agreement — one invoice, one admin dashboard, one support relationship. Pricing is custom based on total student count across the district. Contact us to start a conversation.",
  },
];

function FeatureList({
  features,
  light = false,
}: {
  features: string[];
  light?: boolean;
}) {
  return (
    <ul className="space-y-2.5">
      {features.map((f) => (
        <li key={f} className="flex items-start gap-2.5 text-sm">
          <Check
            className={`mt-0.5 h-4 w-4 shrink-0 ${light ? "text-green-400" : "text-green-500"}`}
          />
          <span className={light ? "text-gray-300" : "text-gray-600"}>{f}</span>
        </li>
      ))}
    </ul>
  );
}

export default function PricingPage() {
  return (
    <div className="px-4 py-16 sm:py-24">
      <div className="mx-auto max-w-7xl">
        {/* Header */}
        <div className="text-center">
          <h1 className="text-4xl font-bold tracking-tight text-gray-900">
            Simple, honest pricing for schools
          </h1>
          <p className="mt-4 text-lg text-gray-500">
            Start free with no credit card. Upgrade when your school is ready to grow.
          </p>
        </div>

        {/* Plans */}
        <div id="plans" className="mt-14 grid items-stretch gap-6 md:grid-cols-3">
          {/* Platform Starter — Free */}
          <Card className="flex flex-col border shadow-sm">
            <CardHeader className="pb-4">
              <div className="mb-2 flex items-center gap-2 text-sm font-semibold tracking-wide text-gray-400 uppercase">
                <Zap className="h-4 w-4" />
                Platform Starter
              </div>
              <div>
                <span className="text-4xl font-bold text-gray-900">$0</span>
                <span className="ml-1 text-sm text-gray-500">forever</span>
              </div>
              <p className="mt-2 text-sm text-gray-500">
                Full access to pre-built curricula for schools getting started.
              </p>
            </CardHeader>
            <CardContent className="flex flex-1 flex-col justify-between space-y-6">
              <FeatureList features={STARTER_FEATURES} />
              <LinkButton
                variant="outline"
                className="w-full justify-center"
                href="/school/register"
              >
                Get started free
              </LinkButton>
            </CardContent>
          </Card>

          {/* School Pro — highlighted */}
          <Card className="relative flex flex-col border-2 border-indigo-600 shadow-lg">
            <Badge className="absolute -top-3 left-1/2 -translate-x-1/2 bg-indigo-600 px-3">
              Most popular
            </Badge>
            <CardHeader className="pb-4">
              <div className="mb-2 flex items-center gap-2 text-sm font-semibold tracking-wide text-indigo-600 uppercase">
                <School className="h-4 w-4" />
                School Pro
              </div>
              <div>
                <span className="text-4xl font-bold text-gray-900">~$5</span>
                <span className="ml-1 text-sm text-gray-500">/ student / year</span>
              </div>
              <p className="mt-2 text-sm text-gray-500">
                Billed annually. About the cost of one textbook per student.
              </p>
            </CardHeader>
            <CardContent className="flex flex-1 flex-col justify-between space-y-6">
              <FeatureList features={PRO_FEATURES} />
              <LinkButton className="w-full justify-center" href="/contact">
                Get a quote
              </LinkButton>
            </CardContent>
          </Card>

          {/* Enterprise */}
          <Card className="flex flex-col border bg-gray-900 text-white shadow-sm">
            <CardHeader className="pb-4">
              <div className="mb-2 flex items-center gap-2 text-sm font-semibold tracking-wide text-gray-400 uppercase">
                <Building2 className="h-4 w-4" />
                School Enterprise
              </div>
              <div>
                <span className="text-4xl font-bold text-white">Custom</span>
              </div>
              <p className="mt-2 text-sm text-gray-400">
                District-wide licensing. One invoice, one contract, one relationship.
              </p>
            </CardHeader>
            <CardContent className="flex flex-1 flex-col justify-between space-y-6">
              <FeatureList features={ENTERPRISE_FEATURES} light />
              <LinkButton
                variant="secondary"
                className="w-full justify-center"
                href="/contact"
              >
                Contact us
              </LinkButton>
            </CardContent>
          </Card>
        </div>

        {/* Comparison callout */}
        <div className="mt-10 rounded-xl border border-indigo-100 bg-indigo-50 px-6 py-5 text-center">
          <p className="text-sm text-indigo-700">
            <span className="font-semibold">Not sure which plan fits?</span> Our pre-built
            content costs you nothing to serve — you only pay when you need custom
            curriculum builds, advanced analytics, or room to grow.{" "}
            <a href="/contact" className="underline hover:no-underline">
              Talk to us
            </a>{" "}
            and we will figure it out together.
          </p>
        </div>

        {/* FAQ */}
        <div className="mx-auto mt-20 max-w-3xl">
          <h2 className="mb-8 text-center text-2xl font-bold text-gray-900">
            Frequently asked questions
          </h2>
          <Accordion hiddenUntilFound>
            {FAQ.map((item, i) => (
              <AccordionItem key={i} value={`faq-${i}`}>
                <AccordionTrigger className="text-left">{item.q}</AccordionTrigger>
                <AccordionContent className="text-gray-600">{item.a}</AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </div>
      </div>
    </div>
  );
}
