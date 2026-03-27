import Link from "next/link";
import { useTranslations } from "next-intl";
import { BookOpen } from "lucide-react";

export function Footer() {
  const t = useTranslations("footer");
  const year = new Date().getFullYear();

  return (
    <footer className="border-t bg-gray-50">
      <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
        <div className="grid grid-cols-2 gap-8 md:grid-cols-4">
          {/* Brand */}
          <div className="col-span-2 md:col-span-1">
            <Link href="/" className="flex items-center gap-2 font-bold text-lg">
              <BookOpen className="h-5 w-5 text-blue-600" />
              <span>StudyBuddy</span>
            </Link>
            <p className="mt-2 text-sm text-gray-500">{t("tagline")}</p>
          </div>

          {/* Product */}
          <div>
            <h3 className="text-sm font-semibold text-gray-900">{t("product")}</h3>
            <ul className="mt-3 space-y-2 text-sm text-gray-500">
              <li><Link href="/#features" className="hover:text-gray-900">{t("features")}</Link></li>
              <li><Link href="/pricing" className="hover:text-gray-900">{t("pricing")}</Link></li>
              <li><Link href="/pricing#schools" className="hover:text-gray-900">{t("for_schools")}</Link></li>
            </ul>
          </div>

          {/* Company */}
          <div>
            <h3 className="text-sm font-semibold text-gray-900">{t("company")}</h3>
            <ul className="mt-3 space-y-2 text-sm text-gray-500">
              <li><Link href="/contact" className="hover:text-gray-900">{t("contact")}</Link></li>
            </ul>
          </div>

          {/* Legal */}
          <div>
            <h3 className="text-sm font-semibold text-gray-900">{t("legal")}</h3>
            <ul className="mt-3 space-y-2 text-sm text-gray-500">
              <li><Link href="/terms" className="hover:text-gray-900">{t("terms")}</Link></li>
              <li><Link href="/privacy" className="hover:text-gray-900">{t("privacy")}</Link></li>
            </ul>
          </div>
        </div>

        <div className="mt-8 border-t pt-6 text-center text-sm text-gray-400">
          {t("rights", { year })}
        </div>
      </div>
    </footer>
  );
}
