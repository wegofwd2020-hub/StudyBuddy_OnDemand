import type { Metadata } from "next";
import { useTranslations } from "next-intl";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AnchorButton, LinkButton } from "@/components/ui/link-button";
import { BookOpen } from "lucide-react";

export const metadata: Metadata = { title: "Sign In" };

export default function LoginPage() {
  const t = useTranslations("auth");

  return (
    <div className="flex min-h-[80vh] items-center justify-center px-4 py-12">
      <Card className="w-full max-w-sm shadow-lg">
        <CardHeader className="text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-blue-50 mb-2">
            <BookOpen className="h-6 w-6 text-blue-600" />
          </div>
          <CardTitle className="text-2xl">{t("login_title")}</CardTitle>
          <p className="text-sm text-gray-500">{t("login_subtitle")}</p>
        </CardHeader>
        <CardContent className="space-y-4">
          <AnchorButton className="w-full justify-center" href="/auth/login">
            {t("login_btn")}
          </AnchorButton>
          <p className="text-center text-sm text-gray-500">
            Don&apos;t have an account?{" "}
            <Link href="/signup" className="text-blue-600 hover:underline">
              Sign up free
            </Link>
          </p>
          <p className="text-center text-sm">
            <Link
              href="/reset-password"
              className="text-gray-500 hover:text-gray-900 hover:underline"
            >
              {t("forgot_password")}
            </Link>
          </p>
          <div className="relative my-2">
            <div className="absolute inset-0 flex items-center">
              <span className="w-full border-t" />
            </div>
            <div className="relative flex justify-center text-xs text-gray-400">
              <span className="bg-white px-2">or</span>
            </div>
          </div>
          <p className="text-center text-sm text-gray-500">
            Are you a teacher or school admin?{" "}
            <Link href="/school/login" className="text-blue-600 hover:underline">
              School sign in
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
