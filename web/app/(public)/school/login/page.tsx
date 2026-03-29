import type { Metadata } from "next";
import { useTranslations } from "next-intl";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AnchorButton } from "@/components/ui/link-button";
import { School } from "lucide-react";

export const metadata: Metadata = { title: "School Sign In" };

export default function SchoolLoginPage() {
  const t = useTranslations("auth");

  return (
    <div className="flex min-h-[80vh] items-center justify-center px-4 py-12">
      <Card className="w-full max-w-sm shadow-lg">
        <CardHeader className="text-center">
          <div className="mx-auto mb-2 flex h-12 w-12 items-center justify-center rounded-full bg-indigo-50">
            <School className="h-6 w-6 text-indigo-600" />
          </div>
          <CardTitle className="text-2xl">{t("school_login_title")}</CardTitle>
          <p className="text-sm text-gray-500">{t("school_login_subtitle")}</p>
        </CardHeader>
        <CardContent className="space-y-4">
          <AnchorButton
            className="w-full justify-center bg-indigo-600 hover:bg-indigo-700"
            href="/auth/login?connection=school"
          >
            {t("login_btn")}
          </AnchorButton>
          <p className="text-center text-sm text-gray-500">
            Looking for student sign in?{" "}
            <Link href="/login" className="text-blue-600 hover:underline">
              Student login
            </Link>
          </p>
          <p className="text-center text-sm text-gray-500">
            Don&apos;t have a school account?{" "}
            <Link href="/contact" className="text-blue-600 hover:underline">
              Contact us
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
