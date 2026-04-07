import Image from "next/image";
import { useTranslations } from "next-intl";
import { Card, CardContent } from "@/components/ui/card";
import { LinkButton } from "@/components/ui/link-button";
import { DemoRequestModal } from "@/components/demo/DemoRequestModal";
import { DemoTeacherRequestModal } from "@/components/demo/DemoTeacherRequestModal";
import { Zap, Volume2, Globe, WifiOff, ClipboardList, School } from "lucide-react";

export default function LandingPage() {
  return (
    <>
      {/* Home banner — 2.5 inches (240 px) tall, full width */}
      <div className="relative h-[240px] w-full">
        <Image
          src="/assets/home_banner.png"
          alt="StudyBuddy — learning for every family"
          fill
          priority
          className="object-contain object-center"
        />
      </div>
      <HeroSection />
      <FeaturesSection />
      <SocialProofSection />
      <CtaSection />
    </>
  );
}

// "Study Buddy" translated into 8 languages — shown as a decorative background
// watermark to convey the meaning: a companion that helps a student learn.
const STUDY_BUDDY_TRANSLATIONS = [
  "Study Buddy",          // English
  "Compañero de Estudio", // Spanish
  "Camarade d'Étude",     // French
  "Lernbegleiter",        // German
  "படிப்பு தோழன்",          // Tamil
  "पढ़ाई का साथी",          // Hindi
  "చదువు స్నేహితుడు",       // Telugu
  "ಅಧ್ಯಯನ ಸ್ನೇಹಿತ",         // Kannada
  "പഠന കൂട്ടുകാരൻ",        // Malayalam
];

// Vary font sizes by position to give a natural scattered feel
const SIZE_CLASSES = ["text-sm", "text-base", "text-lg", "text-xl", "text-sm", "text-base"];

function HeroSection() {
  const t = useTranslations("landing");
  // Repeat enough times to fill the background across all viewport sizes
  const repeated = Array.from({ length: 5 }, () => STUDY_BUDDY_TRANSLATIONS).flat();
  return (
    <section className="relative overflow-hidden bg-gradient-to-b from-blue-50 to-white px-4 py-20 text-center sm:py-28">
      {/* Decorative multilingual watermark — purely visual, hidden from assistive tech */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 flex flex-wrap content-start gap-x-10 gap-y-5 p-6 select-none opacity-[0.12]"
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
          {t("hero_heading")}
        </h1>
        <p className="mt-3 text-xl font-medium text-blue-600">{t("hero_tagline")}</p>
        <p className="mt-4 text-lg text-gray-600">{t("hero_subheading")}</p>
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          <DemoRequestModal />
          <DemoTeacherRequestModal />
        </div>
      </div>
    </section>
  );
}

const FEATURES = [
  { icon: Zap, key: "instant" },
  { icon: Volume2, key: "audio" },
  { icon: Globe, key: "multilang" },
  { icon: WifiOff, key: "offline" },
  { icon: ClipboardList, key: "experiments" },
  { icon: School, key: "schools" },
] as const;

function FeaturesSection() {
  const t = useTranslations("landing");
  return (
    <section id="features" className="bg-white px-4 py-20">
      <div className="mx-auto max-w-7xl">
        <h2 className="text-center text-3xl font-bold text-gray-900">
          {t("features_heading")}
        </h2>
        <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map(({ icon: Icon, key }) => (
            <Card key={key} className="border shadow-sm">
              <CardContent className="p-6">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-50">
                  <Icon className="h-5 w-5 text-blue-600" />
                </div>
                <h3 className="mt-4 font-semibold text-gray-900">
                  {t(`feature_${key}_title` as Parameters<typeof t>[0])}
                </h3>
                <p className="mt-2 text-sm text-gray-500">
                  {t(`feature_${key}_desc` as Parameters<typeof t>[0])}
                </p>
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
    quote: "My daughter went from a C to a B+ in her favourite subject in one semester.",
    author: "Maria T., Parent",
  },
  {
    quote:
      "The audio lessons are a game-changer for my students with reading difficulties.",
    author: "James K., Grade 8 Teacher",
  },
  {
    quote: "Finally an app that works when I'm on the bus with no signal.",
    author: "Priya, Grade 10 Student",
  },
];

function SocialProofSection() {
  const t = useTranslations("landing");
  return (
    <section className="bg-gray-50 px-4 py-20">
      <div className="mx-auto max-w-7xl">
        <h2 className="text-center text-3xl font-bold text-gray-900">
          {t("social_proof_heading")}
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
  const t = useTranslations("landing");
  return (
    <section className="bg-blue-600 px-4 py-20 text-center text-white">
      <div className="mx-auto max-w-2xl">
        <h2 className="text-3xl font-bold">{t("cta_heading")}</h2>
        <p className="mt-4 text-blue-100">{t("cta_subheading")}</p>
        <LinkButton size="lg" variant="secondary" className="mt-8" href="/signup">
          {t("cta_btn")}
        </LinkButton>
      </div>
    </section>
  );
}
