import type { Metadata } from "next";
import Link from "next/link";
import { LinkButton } from "@/components/ui/link-button";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import {
  BookOpen,
  Globe,
  BarChart2,
  Upload,
  ShieldCheck,
  HardDrive,
  Users,
  Palette,
  CheckCircle2,
} from "lucide-react";

export const metadata: Metadata = {
  title: "For Schools",
  description:
    "Pre-built curricula, teacher tools, and three languages — everything your school needs. Free to start.",
};

export default function ForSchoolsPage() {
  return (
    <>
      <HeroSection />
      <HowItWorksSection />
      <FeaturesSection />
      <PricingSection />
      <FaqSection />
      <CtaSection />
    </>
  );
}

function HeroSection() {
  return (
    <section className="bg-gradient-to-b from-blue-600 to-blue-700 px-4 py-20 text-center text-white">
      <div className="mx-auto max-w-3xl">
        <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
          StudyBuddy for Schools
        </h1>
        <p className="mt-6 text-xl text-blue-50">
          Pre-built curricula. Teacher tools. Three languages.
          <br className="hidden sm:block" />
          Everything your school needs — free to start.
        </p>
        <div className="mt-8 flex flex-wrap justify-center gap-4">
          <LinkButton href="/school/register" size="lg" variant="secondary">
            Register your school
          </LinkButton>
          <LinkButton
            href="/contact"
            size="lg"
            variant="outline"
            className="border-white/40 text-white hover:bg-white/10"
          >
            Book a demo
          </LinkButton>
        </div>
      </div>
    </section>
  );
}

const STEPS = [
  {
    n: "1",
    title: "Register your school (2 minutes)",
    body: "You become the school admin. Add your teachers and students — or let them self-enroll.",
  },
  {
    n: "2",
    title: "Content is ready on day one",
    body: "Grades 5–12 platform curricula are pre-built. No pipeline run, no waiting. Teachers can browse, assign, and customize.",
  },
  {
    n: "3",
    title: "Students learn. Teachers track.",
    body: "Every student gets lessons, quizzes, audio, and activities. Teachers see progress in real time.",
  },
];

function HowItWorksSection() {
  return (
    <section className="bg-white px-4 py-20">
      <div className="mx-auto max-w-3xl">
        <h2 className="text-center text-3xl font-bold text-gray-900">How it works</h2>
        <ol className="mt-12 space-y-8">
          {STEPS.map(({ n, title, body }) => (
            <li key={n} className="flex gap-5">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-blue-600 text-sm font-bold text-white">
                {n}
              </div>
              <div>
                <p className="font-semibold text-gray-900">{title}</p>
                <p className="mt-1 text-sm text-gray-600">{body}</p>
              </div>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}

const FEATURES = [
  {
    icon: BookOpen,
    title: "Curriculum management",
    desc: "Platform curricula for Grades 5–12, ready on day one. Upload your own definitions and own the generated content.",
  },
  {
    icon: Users,
    title: "Classroom management",
    desc: "Create classrooms, assign curriculum packages, manage rosters, and track per-class progress at a glance.",
  },
  {
    icon: BarChart2,
    title: "Teacher analytics & alerts",
    desc: "Six report types, at-risk student alerts, weekly digest emails, and CSV export — all built in.",
  },
  {
    icon: Palette,
    title: "School branding & theming",
    desc: "Upload your logo and set your school's color palette. Students and teachers see your brand throughout.",
  },
  {
    icon: Globe,
    title: "Multi-language content",
    desc: "Every lesson, quiz, and audio narration in English, French, and Spanish. Students switch any time.",
  },
  {
    icon: HardDrive,
    title: "Backup & restore",
    desc: "Scheduled nightly backups of all school curricula with one-click restore and dry-run preview.",
  },
  {
    icon: ShieldCheck,
    title: "FERPA / COPPA compliance",
    desc: "Educational record privacy, under-13 parental consent flow, and data minimization — baked into the data model.",
  },
  {
    icon: Upload,
    title: "Accessibility",
    desc: "WCAG 2.1 Level AA target across all student-facing interfaces, including dyslexia-friendly font mode.",
  },
] as const;

function FeaturesSection() {
  return (
    <section className="bg-gray-50 px-4 py-20">
      <div className="mx-auto max-w-7xl">
        <h2 className="text-center text-3xl font-bold text-gray-900">
          Built for the whole school
        </h2>
        <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {FEATURES.map(({ icon: Icon, title, desc }) => (
            <div
              key={title}
              className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm"
            >
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-50">
                <Icon className="h-5 w-5 text-blue-600" />
              </div>
              <h3 className="mt-4 font-semibold text-gray-900">{title}</h3>
              <p className="mt-2 text-sm text-gray-500">{desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

const TIERS = [
  {
    name: "Platform Starter",
    price: "Free",
    highlight: false,
    bullets: ["Full access to Grades 5–12 content", "Up to 30 students", "English only"],
    cta: "Get started free",
    href: "/school/register",
  },
  {
    name: "School Pro",
    price: "~$5 / student / year",
    highlight: true,
    bullets: [
      "Unlimited students",
      "English, French & Spanish",
      "Custom curriculum builds",
    ],
    cta: "Start School Pro",
    href: "/pricing",
  },
  {
    name: "School Enterprise",
    price: "Custom",
    highlight: false,
    bullets: [
      "District-wide rollout",
      "Dedicated onboarding",
      "SLA & compliance documentation",
    ],
    cta: "Contact us",
    href: "/contact",
  },
] as const;

function PricingSection() {
  return (
    <section className="bg-white px-4 py-20">
      <div className="mx-auto max-w-4xl">
        <h2 className="text-center text-3xl font-bold text-gray-900">Pricing</h2>
        <p className="mt-3 text-center text-gray-500">
          Start free. Upgrade when your school is ready.{" "}
          <Link href="/pricing" className="font-medium text-blue-600 hover:underline">
            See full pricing →
          </Link>
        </p>
        <div className="mt-10 grid gap-6 sm:grid-cols-3">
          {TIERS.map(({ name, price, highlight, bullets, cta, href }) => (
            <div
              key={name}
              className={`rounded-2xl border p-6 ${
                highlight
                  ? "border-blue-600 bg-blue-600 text-white shadow-lg"
                  : "border-gray-200 bg-white"
              }`}
            >
              <h3 className={`font-bold ${highlight ? "text-white" : "text-gray-900"}`}>
                {name}
              </h3>
              <p
                className={`mt-2 text-xl font-bold ${highlight ? "text-white" : "text-gray-900"}`}
              >
                {price}
              </p>
              <ul className="mt-4 space-y-2">
                {bullets.map((b) => (
                  <li key={b} className="flex items-start gap-2 text-sm">
                    <CheckCircle2
                      className={`mt-0.5 h-4 w-4 shrink-0 ${
                        highlight ? "text-blue-200" : "text-blue-600"
                      }`}
                    />
                    <span className={highlight ? "text-blue-50" : "text-gray-600"}>
                      {b}
                    </span>
                  </li>
                ))}
              </ul>
              <LinkButton
                href={href}
                className="mt-6 w-full"
                variant={highlight ? "secondary" : "outline"}
              >
                {cta}
              </LinkButton>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

const FAQS = [
  {
    q: "How long does setup take?",
    a: "Most schools are live in under 20 minutes. Register, add your teachers and students (or let them self-enroll), and content is available immediately.",
  },
  {
    q: "Do students need their own accounts?",
    a: "Yes, but your school admin provisions them. Students receive a temporary password by email and are prompted to set a permanent one on first login.",
  },
  {
    q: "Can we use our own curriculum?",
    a: "Yes. School Pro and Enterprise plans let you upload a curriculum definition. Our pipeline generates lessons, quizzes, and audio for every unit — and your school owns the output.",
  },
  {
    q: "Is content available offline?",
    a: "Yes. The student mobile app caches downloaded content so students can study without an internet connection. Progress syncs automatically when they're back online.",
  },
  {
    q: "How does pricing work for a school of 200 students?",
    a: "School Pro is billed per enrolled student per year. A school of 200 students is roughly $1,000/year — full Grades 5–12 content in three languages with teacher tools included.",
  },
] as const;

function FaqSection() {
  return (
    <section className="bg-gray-50 px-4 py-20">
      <div className="mx-auto max-w-2xl">
        <h2 className="text-center text-3xl font-bold text-gray-900">
          Frequently asked questions
        </h2>
        {/* Collapsed, matching /pricing. Every answer used to render open, which
            put ~600 words of secondary content between the pricing a visitor came
            for and the call to action — and made the page's length its dominant
            impression. An FAQ is not a lesser section; collapsing it is how a page
            answers many questions while still reading as short.
            See docs/DESIGN_kolibri_site_teardown.md. */}
        <div className="mt-10">
          {/* hiddenUntilFound, not a bare <Accordion>: Base UI unmounts a closed
              panel by default (keepMounted defaults false), which would drop every
              answer out of the server-rendered HTML. On a marketing page that trades
              crawlable copy — and Ctrl+F — for the collapse. hidden="until-found"
              keeps the text in the DOM and lets find-in-page open the panel. */}
          <Accordion hiddenUntilFound>
            {FAQS.map(({ q, a }, i) => (
              <AccordionItem key={q} value={`faq-${i}`}>
                <AccordionTrigger className="text-left">{q}</AccordionTrigger>
                <AccordionContent className="text-gray-600">{a}</AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </div>
      </div>
    </section>
  );
}

function CtaSection() {
  return (
    <section className="bg-blue-600 px-4 py-20 text-center text-white">
      <div className="mx-auto max-w-2xl">
        <h2 className="text-3xl font-bold">Ready to get started?</h2>
        <p className="mt-4 text-blue-50">
          Register your school free — no credit card, no commitment.
        </p>
        <div className="mt-8 flex flex-wrap justify-center gap-4">
          <LinkButton href="/school/register" size="lg" variant="secondary">
            Register now
          </LinkButton>
          <LinkButton
            href="/contact"
            size="lg"
            variant="outline"
            className="border-white/40 text-white hover:bg-white/10"
          >
            Contact us
          </LinkButton>
        </div>
        {/* The tour was reachable only from the landing page, so /for-schools --
            our most audience-specific page -- had no route to our
            audience-specific content (docs/DESIGN_public_audience_map.md).
            It sits here rather than in the hero because the reader who stalls at
            "Ready to get started?" is exactly the one who wants to look before
            registering; a third button would compete with the primary CTA
            instead of catching that reader. Naming the three roles is the point
            -- it lets a buyer self-select and see what their staff and students
            get. */}
        <p className="mt-6 text-sm text-blue-50">
          Not ready yet?{" "}
          <Link href="/tour" className="font-semibold text-white underline">
            Explore the platform
          </Link>{" "}
          as a School Admin, Teacher, or Student — no account needed.
        </p>
      </div>
    </section>
  );
}
