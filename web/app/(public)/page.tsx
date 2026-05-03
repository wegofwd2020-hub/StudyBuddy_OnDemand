import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { Card, CardContent } from "@/components/ui/card";
import { LinkButton } from "@/components/ui/link-button";
import {
  Zap,
  BookOpen,
  Globe,
  BarChart2,
  Upload,
  ShieldCheck,
  ArrowRight,
} from "lucide-react";

export const metadata: Metadata = {
  title: "StudyBuddy — AI-powered learning for your whole school",
  description:
    "Register your school once. Every student gets instant AI-powered lessons, quizzes, and audio — aligned to your curriculum, in English, French, and Spanish.",
};

export default function LandingPage() {
  return (
    <>
      {/* Home banner — 2.5 inches (240 px) tall, full width */}
      <div className="relative h-[240px] w-full">
        <Image
          src="/assets/home_banner.png"
          alt="StudyBuddy — learning for every school"
          fill
          priority
          className="object-contain object-center"
        />
      </div>
      <HeroSection />
      <FeaturesSection />
      <TourGatewaySection />
      <SocialProofSection />
      <CtaSection />
    </>
  );
}

// "Study Buddy" translated into 8 languages — shown as a decorative background
// watermark to convey the meaning: a companion that helps a student learn.
const STUDY_BUDDY_TRANSLATIONS = [
  "Learning Companion",
  "Compañero de Aprendizaje",
  "Напарник в обучении",
  "Compagnon d'Apprentissage",
  "Lernbegleiter",
  "கற்றல் தோழன்",
  "सीखने का साथी",
  "అభ్యాస సహచరుడు",
  "ಕಲಿಕೆಯ ಸಂಗಾತಿ",
  "പഠന സഹചാരി",
];

const SIZE_CLASSES = ["text-sm", "text-base", "text-lg", "text-xl", "text-sm", "text-base"];

function HeroSection() {
  const repeated = Array.from({ length: 5 }, () => STUDY_BUDDY_TRANSLATIONS).flat();
  return (
    <section className="relative overflow-hidden bg-gradient-to-b from-blue-50 to-white px-4 py-20 text-center sm:py-28">
      {/* Decorative multilingual watermark — purely visual, hidden from assistive tech */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 flex flex-wrap content-start gap-x-10 gap-y-5 p-6 select-none opacity-[0.22]"
      >
        {repeated.map((phrase, i) => (
          <span
            key={i}
            className={`${SIZE_CLASSES[i % SIZE_CLASSES.length]} font-semibold text-blue-800 whitespace-nowrap`}
          >
            {phrase}
          </span>
        ))}
      </div>

      <div className="relative mx-auto max-w-3xl">
        <h1 className="text-4xl font-bold tracking-tight text-gray-900 sm:text-5xl lg:text-6xl">
          Your bridge from lessons to a world that&apos;s always current.
        </h1>
        <p className="mt-6 text-xl text-gray-600">
          Give every student at your school instant AI-powered lessons, quizzes, and audio —
          aligned to your curriculum, in English, French, and Spanish.
        </p>
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          <LinkButton size="lg" href="/school/register">
            Register your school — it&apos;s free
          </LinkButton>
          <LinkButton size="lg" variant="outline" href="/tour/school-admin">
            See how it works
          </LinkButton>
        </div>
        <div className="mt-4">
          <Link
            href="/school/login"
            className="inline-flex items-center gap-1.5 text-sm font-medium text-blue-600 hover:underline"
          >
            Already a teacher? Sign in
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </div>
    </section>
  );
}

const FEATURES = [
  {
    icon: Zap,
    title: "Live in minutes",
    desc: "Register once. Every teacher and student at your school gets instant access — no per-account setup.",
  },
  {
    icon: BookOpen,
    title: "Curricula ready on day one",
    desc: "Pre-built Grades 5–12 content loads immediately. No waiting for AI to generate anything.",
  },
  {
    icon: Globe,
    title: "Three languages, one platform",
    desc: "Every lesson, quiz, and audio narration in English, French, and Spanish. Students switch any time.",
  },
  {
    icon: BarChart2,
    title: "Teachers stay informed",
    desc: "Real-time progress reports, at-risk alerts, and weekly digests — all without leaving the portal.",
  },
  {
    icon: Upload,
    title: "Your curriculum, your way",
    desc: "Upload your own curriculum definition. We build the content. Your school owns it.",
  },
  {
    icon: ShieldCheck,
    title: "Built for compliance",
    desc: "FERPA, COPPA, and WCAG 2.1 AA — not afterthoughts. Baked into the data model from day one.",
  },
] as const;

function FeaturesSection() {
  return (
    <section id="features" className="bg-white px-4 py-20">
      <div className="mx-auto max-w-7xl">
        <h2 className="text-center text-3xl font-bold text-gray-900">
          Everything your school needs, on day one
        </h2>
        <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map(({ icon: Icon, title, desc }) => (
            <Card key={title} className="border shadow-sm">
              <CardContent className="p-6">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-50">
                  <Icon className="h-5 w-5 text-blue-600" />
                </div>
                <h3 className="mt-4 font-semibold text-gray-900">{title}</h3>
                <p className="mt-2 text-sm text-gray-500">{desc}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
}

const TESTIMONIALS = [
  {
    quote:
      "We were live across the whole school in under 20 minutes. The pre-built curricula meant every class had content on day one.",
    author: "Sarah M., School Principal",
  },
  {
    quote:
      "The audio lessons are a game-changer for my students with reading difficulties. Three languages in one platform is unheard of at this price.",
    author: "James K., Grade 8 Teacher",
  },
  {
    quote: "Finally an app that works when I'm on the bus with no signal.",
    author: "Priya, Grade 10 Student",
  },
];

function TourGatewaySection() {
  return (
    <section className="border-y bg-violet-50 px-4 py-16">
      <div className="mx-auto max-w-3xl text-center">
        <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-violet-500">
          No account needed
        </p>
        <h2 className="mb-3 text-2xl font-bold text-gray-900 sm:text-3xl">
          See exactly what you can do
        </h2>
        <p className="mb-8 text-base text-gray-500">
          Walk through the platform from the perspective of a School Admin, Teacher, or Student —
          before you register.
        </p>
        <Link
          href="/tour"
          className="inline-flex items-center gap-2 rounded-lg bg-violet-600 px-6 py-3 text-sm font-bold text-white shadow-sm hover:bg-violet-700"
        >
          Explore the platform
          <ArrowRight className="h-4 w-4" />
        </Link>
      </div>
    </section>
  );
}

function SocialProofSection() {
  return (
    <section className="bg-gray-50 px-4 py-20">
      <div className="mx-auto max-w-7xl">
        <h2 className="text-center text-3xl font-bold text-gray-900">
          Trusted by schools, teachers, and students
        </h2>
        <div className="mt-10 grid gap-6 sm:grid-cols-3">
          {TESTIMONIALS.map((item) => (
            <Card key={item.author} className="bg-white shadow-sm">
              <CardContent className="p-6">
                <p className="text-gray-600 italic">&ldquo;{item.quote}&rdquo;</p>
                <p className="mt-4 text-sm font-medium text-gray-900">— {item.author}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
}

function CtaSection() {
  return (
    <section className="bg-blue-600 px-4 py-20 text-center text-white">
      <div className="mx-auto max-w-2xl">
        <h2 className="text-3xl font-bold">Ready to bring StudyBuddy to your school?</h2>
        <p className="mt-4 text-blue-100">
          Free to start. No credit card. Full access to Grades 5–12 content on day one.
        </p>
        <LinkButton size="lg" variant="secondary" className="mt-8" href="/school/register">
          Register your school free
        </LinkButton>
      </div>
    </section>
  );
}
