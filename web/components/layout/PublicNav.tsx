"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { LinkButton } from "@/components/ui/link-button";
import { BookOpen, Menu, X } from "lucide-react";
import { useState } from "react";
import { IS_DEMO_MODE } from "@/lib/demo-mode";
import { TestRunRequestModal } from "@/components/demo/TestRunRequestModal";

export function PublicNav() {
  const [open, setOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-white/95 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2 text-xl font-bold">
          <BookOpen className="h-6 w-6 text-blue-600" />
          <span>StudyBuddy</span>
        </Link>

        {/* Desktop nav */}
        <nav className="hidden items-center gap-6 text-sm font-medium text-gray-600 md:flex">
          {!IS_DEMO_MODE && (
            <>
              <Link href="/for-schools" className="transition-colors hover:text-gray-900">
                For Schools
              </Link>
              <Link href="/pricing" className="transition-colors hover:text-gray-900">
                Pricing
              </Link>
            </>
          )}
          <Link href="/about" className="transition-colors hover:text-gray-900">
            About
          </Link>
          <Link href="/contact" className="transition-colors hover:text-gray-900">
            Contact
          </Link>
        </nav>

        {/* Desktop CTAs.
            Demo mode: "Login" (ghost) for visitors who already have credentials,
            sitting left of the solid "Try a test run" CTA which opens
            TestRunRequestModal so first-time visitors can request their own
            teacher + student credentials.
            Marketing site: "Sign in" + "Register your school" (unchanged). */}
        <div className="hidden items-center gap-3 md:flex">
          {IS_DEMO_MODE ? (
            <>
              <LinkButton variant="ghost" href="/signin">
                Login
              </LinkButton>
              <TestRunRequestModal
                trigger={<Button variant="default">Try a test run</Button>}
              />
            </>
          ) : (
            <>
              <LinkButton variant="ghost" href="/signin">
                Sign in
              </LinkButton>
              <LinkButton href="/school/register">Register your school</LinkButton>
            </>
          )}
        </div>

        {/* Mobile hamburger */}
        <button
          className="rounded-md p-2 text-gray-600 hover:text-gray-900 md:hidden"
          onClick={() => setOpen(!open)}
          aria-label="Toggle menu"
        >
          {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>

      {/* Mobile menu */}
      {open && (
        <div className="space-y-3 border-t bg-white px-4 py-4 md:hidden">
          {!IS_DEMO_MODE && (
            <>
              <Link
                href="/for-schools"
                className="block text-sm font-medium text-gray-600 hover:text-gray-900"
                onClick={() => setOpen(false)}
              >
                For Schools
              </Link>
              <Link
                href="/pricing"
                className="block text-sm font-medium text-gray-600 hover:text-gray-900"
                onClick={() => setOpen(false)}
              >
                Pricing
              </Link>
            </>
          )}
          <Link
            href="/about"
            className="block text-sm font-medium text-gray-600 hover:text-gray-900"
            onClick={() => setOpen(false)}
          >
            About
          </Link>
          <Link
            href="/contact"
            className="block text-sm font-medium text-gray-600 hover:text-gray-900"
            onClick={() => setOpen(false)}
          >
            Contact
          </Link>
          <div className="flex flex-col gap-2 pt-2">
            {IS_DEMO_MODE ? (
              <>
                <LinkButton variant="outline" href="/signin">
                  Login
                </LinkButton>
                <TestRunRequestModal
                  trigger={
                    <Button variant="default" className="w-full">
                      Try a test run
                    </Button>
                  }
                />
              </>
            ) : (
              <>
                <LinkButton variant="outline" href="/signin">
                  Sign in
                </LinkButton>
                <LinkButton href="/school/register">Register your school</LinkButton>
              </>
            )}
          </div>
        </div>
      )}
    </header>
  );
}
