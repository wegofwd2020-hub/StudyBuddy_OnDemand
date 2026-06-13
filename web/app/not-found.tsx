"use client";

import { useEffect, useState } from "react";
import { LinkButton } from "@/components/ui/link-button";

// Send "Go home" to the signed-in user's own portal home instead of the public
// landing/login page, which reads as an unexpected logout (feedback #447).
function homeHref(): string {
  if (typeof window === "undefined") return "/";
  try {
    if (localStorage.getItem("sb_admin_token")) return "/admin";
    if (localStorage.getItem("sb_teacher_token")) return "/school/dashboard";
    if (localStorage.getItem("sb_token")) return "/student/dashboard";
  } catch {
    // localStorage blocked (private mode) — fall back to the public home.
  }
  return "/";
}

export default function NotFound() {
  // Default to "/" for SSR/first paint, then resolve the portal home on the
  // client so the markup matches and there's no hydration mismatch.
  const [href, setHref] = useState("/");
  useEffect(() => setHref(homeHref()), []);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-4 text-center">
      <h1 className="text-6xl font-bold text-gray-200">404</h1>
      <h2 className="mt-4 text-2xl font-semibold text-gray-900">Page not found</h2>
      <p className="mt-2 text-gray-500">
        The page you&apos;re looking for doesn&apos;t exist.
      </p>
      <LinkButton className="mt-6" href={href}>
        Go home
      </LinkButton>
    </div>
  );
}
