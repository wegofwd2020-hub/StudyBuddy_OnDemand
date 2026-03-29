import type { Metadata } from "next";
import { useTranslations } from "next-intl";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { LinkButton } from "@/components/ui/link-button";
import { Check } from "lucide-react";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";

export const metadata: Metadata = { title: "Pricing" };

const FREE_FEATURES = ["free_lessons", "audio_included"] as const;

const STUDENT_FEATURES = [
  "unlimited_lessons",
  "audio_included",
  "all_languages",
  "offline_access",
  "experiments",
  "progress_tracking",
] as const;

const SCHOOL_FEATURES = [
  "unlimited_lessons",
  "audio_included",
  "all_languages",
  "offline_access",
  "experiments",
  "progress_tracking",
  "teacher_reports",
  "custom_curriculum",
] as const;

const FAQ = [
  {
    q: "Is there a free trial?",
    a: "Yes. Every account starts with 5 free lessons per month, no credit card required.",
  },
  {
    q: "Can I switch plans at any time?",
    a: "Yes. You can upgrade or downgrade your plan at any time. Changes take effect on your next billing cycle.",
  },
  {
    q: "What languages are supported?",
    a: "All AI-generated content is available in English, French, and Spanish. UI is also available in all three languages.",
  },
  {
    q: "How does school pricing work?",
    a: "School plans are flat-rate monthly or annual subscriptions covering all students and teachers at the school. Contact us for a custom quote.",
  },
  {
    q: "Is there a COPPA-compliant option for under-13 students?",
    a: "Yes. Students under 13 require parental consent before their account activates. We handle the consent flow automatically.",
  },
];

export default function PricingPage() {
  const t = useTranslations("pricing");

  return (
    <div className="px-4 py-16 sm:py-24">
      <div className="mx-auto max-w-7xl">
        <div className="text-center">
          <h1 className="text-4xl font-bold text-gray-900">{t("heading")}</h1>
          <p className="mt-4 text-lg text-gray-500">{t("subheading")}</p>
        </div>

        <div id="plans" className="mt-12 grid items-start gap-6 md:grid-cols-3">
          {/* Free */}
          <Card className="border shadow-sm">
            <CardHeader>
              <CardTitle className="text-gray-500">{t("free_plan")}</CardTitle>
              <div className="mt-2">
                <span className="text-4xl font-bold text-gray-900">$0</span>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <ul className="space-y-2">
                {FREE_FEATURES.map((f) => (
                  <li key={f} className="flex items-center gap-2 text-sm text-gray-600">
                    <Check className="h-4 w-4 shrink-0 text-green-500" />
                    {t(f)}
                  </li>
                ))}
              </ul>
              <LinkButton
                variant="outline"
                className="w-full justify-center"
                href="/signup"
              >
                {t("start_free")}
              </LinkButton>
            </CardContent>
          </Card>

          {/* Student */}
          <Card className="relative border-2 border-blue-600 shadow-lg">
            <Badge className="absolute -top-3 left-1/2 -translate-x-1/2 bg-blue-600">
              Most popular
            </Badge>
            <CardHeader>
              <CardTitle>{t("student_plan")}</CardTitle>
              <div className="mt-2">
                <span className="text-4xl font-bold text-gray-900">$9.99</span>
                <span className="text-sm text-gray-500">{t("per_month")}</span>
              </div>
              <p className="text-xs text-gray-400">
                or $99.99{t("per_year")} — {t("save_badge")}
              </p>
            </CardHeader>
            <CardContent className="space-y-4">
              <ul className="space-y-2">
                {STUDENT_FEATURES.map((f) => (
                  <li key={f} className="flex items-center gap-2 text-sm text-gray-600">
                    <Check className="h-4 w-4 shrink-0 text-green-500" />
                    {t(f)}
                  </li>
                ))}
              </ul>
              <LinkButton className="w-full justify-center" href="/signup">
                {t("subscribe_now")}
              </LinkButton>
            </CardContent>
          </Card>

          {/* School */}
          <Card id="schools" className="border bg-gray-900 text-white shadow-sm">
            <CardHeader>
              <CardTitle className="text-white">{t("school_plan")}</CardTitle>
              <div className="mt-2">
                <span className="text-4xl font-bold">$299+</span>
                <span className="text-sm text-gray-300">{t("per_month")}</span>
              </div>
              <p className="text-xs text-gray-400">Custom pricing per school size</p>
            </CardHeader>
            <CardContent className="space-y-4">
              <ul className="space-y-2">
                {SCHOOL_FEATURES.map((f) => (
                  <li key={f} className="flex items-center gap-2 text-sm text-gray-300">
                    <Check className="h-4 w-4 shrink-0 text-green-400" />
                    {t(f)}
                  </li>
                ))}
              </ul>
              <LinkButton
                variant="secondary"
                className="w-full justify-center"
                href="/contact"
              >
                {t("contact_sales")}
              </LinkButton>
            </CardContent>
          </Card>
        </div>

        {/* FAQ */}
        <div className="mx-auto mt-20 max-w-3xl">
          <h2 className="mb-8 text-center text-2xl font-bold text-gray-900">
            {t("faq_heading")}
          </h2>
          <Accordion>
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
