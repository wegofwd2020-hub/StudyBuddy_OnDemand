import type { Metadata } from "next";
import { useTranslations } from "next-intl";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AnchorButton } from "@/components/ui/link-button";
import { BookOpen, Check } from "lucide-react";

export const metadata: Metadata = { title: "Create Account" };

const PERKS = [
  "5 free lessons every month",
  "Audio narration for every lesson",
  "No credit card required",
];

export default function SignupPage() {
  const t = useTranslations("auth");

  return (
    <div className="flex min-h-[80vh] items-center justify-center px-4 py-12">
      <div className="w-full max-w-sm">
        <Card className="shadow-lg">
          <CardHeader className="text-center">
            <div className="mx-auto mb-2 flex h-12 w-12 items-center justify-center rounded-full bg-blue-50">
              <BookOpen className="h-6 w-6 text-blue-600" />
            </div>
            <CardTitle className="text-2xl">{t("signup_title")}</CardTitle>
            <p className="text-sm text-gray-500">{t("signup_subtitle")}</p>
          </CardHeader>
          <CardContent className="space-y-4">
            <ul className="mb-2 space-y-2">
              {PERKS.map((perk) => (
                <li key={perk} className="flex items-center gap-2 text-sm text-gray-600">
                  <Check className="h-4 w-4 shrink-0 text-green-500" />
                  {perk}
                </li>
              ))}
            </ul>
            <AnchorButton
              className="w-full justify-center"
              href="/auth/login?screen_hint=signup"
            >
              Create free account
            </AnchorButton>
            <p className="text-center text-sm text-gray-500">
              Already have an account?{" "}
              <Link href="/login" className="text-blue-600 hover:underline">
                Sign in
              </Link>
            </p>
            <p className="text-center text-xs text-gray-400">
              By signing up, you agree to our{" "}
              <Link href="/terms" className="underline">
                Terms
              </Link>{" "}
              and{" "}
              <Link href="/privacy" className="underline">
                Privacy Policy
              </Link>
              .
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
