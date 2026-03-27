"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { LinkButton } from "@/components/ui/link-button";
import { BookOpen, Menu, X } from "lucide-react";
import { useState } from "react";

export function PublicNav() {
  const t = useTranslations("nav");
  const [open, setOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-white/95 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2 font-bold text-xl">
          <BookOpen className="h-6 w-6 text-blue-600" />
          <span>StudyBuddy</span>
        </Link>

        {/* Desktop nav */}
        <nav className="hidden md:flex items-center gap-6 text-sm font-medium text-gray-600">
          <Link href="/#features" className="hover:text-gray-900 transition-colors">
            {t("features")}
          </Link>
          <Link href="/pricing" className="hover:text-gray-900 transition-colors">
            {t("pricing")}
          </Link>
          <Link href="/pricing#schools" className="hover:text-gray-900 transition-colors">
            {t("for_schools")}
          </Link>
        </nav>

        {/* Desktop CTA */}
        <div className="hidden md:flex items-center gap-3">
          <LinkButton variant="ghost" href="/login">
            {t("sign_in")}
          </LinkButton>
          <LinkButton href="/signup">{t("start_free")}</LinkButton>
        </div>

        {/* Mobile hamburger */}
        <button
          className="md:hidden p-2 rounded-md text-gray-600 hover:text-gray-900"
          onClick={() => setOpen(!open)}
          aria-label="Toggle menu"
        >
          {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>

      {/* Mobile menu */}
      {open && (
        <div className="md:hidden border-t bg-white px-4 py-4 space-y-3">
          <Link
            href="/#features"
            className="block text-sm font-medium text-gray-600 hover:text-gray-900"
            onClick={() => setOpen(false)}
          >
            {t("features")}
          </Link>
          <Link
            href="/pricing"
            className="block text-sm font-medium text-gray-600 hover:text-gray-900"
            onClick={() => setOpen(false)}
          >
            {t("pricing")}
          </Link>
          <Link
            href="/pricing#schools"
            className="block text-sm font-medium text-gray-600 hover:text-gray-900"
            onClick={() => setOpen(false)}
          >
            {t("for_schools")}
          </Link>
          <div className="pt-2 flex flex-col gap-2">
            <LinkButton variant="outline" href="/login">
              {t("sign_in")}
            </LinkButton>
            <LinkButton href="/signup">{t("start_free")}</LinkButton>
          </div>
        </div>
      )}
    </header>
  );
}
