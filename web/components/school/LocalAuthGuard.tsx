"use client";

/**
 * LocalAuthGuard — client-side gate for Phase A local-auth school portal sessions.
 *
 * The server layout detects a local-auth session via the `sb_local_teacher_session`
 * cookie (set at login) and renders this component instead of the Auth0-guarded
 * path.  This component then:
 *
 *   1. Reads `sb_teacher_token` from localStorage (SSR-safe — runs in useEffect).
 *   2. Decodes the JWT and checks `first_login`.
 *   3. Redirects to /school/change-password?required=1 if first_login=true.
 *   4. Redirects to /school/login (clearing the cookie) if the token is absent
 *      or invalid, so the server layout re-evaluates on next load.
 *   5. Renders the full portal layout (nav, header, main, footer) once verified.
 *
 * Returns null during the initial client-side check to avoid a flash of content
 * before a redirect fires.
 */

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { SchoolNav } from "@/components/layout/SchoolNav";
import { PortalHeader } from "@/components/layout/PortalHeader";
import { PortalFooter } from "@/components/layout/PortalFooter";
import { LimitWarningBanner } from "@/components/school/LimitWarningBanner";
import { HelpWidget } from "@/components/help/HelpWidget";

function decodeJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const base64 = token.split(".")[1];
    const json = atob(base64.replace(/-/g, "+").replace(/_/g, "/"));
    return JSON.parse(json);
  } catch {
    return null;
  }
}

function clearLocalSession() {
  document.cookie =
    "sb_local_teacher_session=; path=/; SameSite=Strict; Max-Age=0";
}

export function LocalAuthGuard({
  children,
  userName,
}: {
  children: React.ReactNode;
  /** Email from the session cookie, used as the display name in PortalHeader. */
  userName: string;
}) {
  const router = useRouter();
  const [verified, setVerified] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("sb_teacher_token");

    if (!token) {
      // No token — session cookie is stale. Clear it and force re-login.
      clearLocalSession();
      router.replace("/school/login");
      return;
    }

    const payload = decodeJwtPayload(token);
    if (!payload) {
      clearLocalSession();
      router.replace("/school/login");
      return;
    }

    // Check token expiry (exp is in seconds).
    const exp = payload.exp as number | undefined;
    if (exp && Date.now() / 1000 > exp) {
      clearLocalSession();
      localStorage.removeItem("sb_teacher_token");
      router.replace("/school/login");
      return;
    }

    if (payload.first_login) {
      // Enforce first-login password change before any portal access (pitfall #24).
      router.replace("/school/change-password?required=1");
      return;
    }

    setVerified(true);
  }, [router]);

  if (!verified) {
    // Return null during the client check to prevent a content flash before
    // a redirect. The server already rendered nothing meaningful here.
    return null;
  }

  return (
    <div className="flex min-h-screen bg-gray-50">
      <SchoolNav />
      <div className="flex flex-1 flex-col overflow-auto">
        <PortalHeader portal="school" userName={userName} />
        <main id="main-content" className="flex-1">
          <LimitWarningBanner />
          {children}
        </main>
        <PortalFooter />
      </div>
      <HelpWidget />
    </div>
  );
}
