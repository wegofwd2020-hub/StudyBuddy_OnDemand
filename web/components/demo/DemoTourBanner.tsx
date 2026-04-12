"use client";

/**
 * DemoTourBanner
 *
 * Shown at the top of a tour page when a valid `demo_token` query param is present.
 * Decodes the JWT payload client-side (no verification — display only).
 * Shows a personalised greeting: "Welcome, [Name] from [School]".
 *
 * If the token is missing, malformed, or expired, the banner is simply not shown
 * and the tour works as a generic public walkthrough.
 */

import { useEffect, useState } from "react";
import { Sparkles } from "lucide-react";

interface DemoPayload {
  name: string;
  school_org: string;
  exp: number;
}

function decodeToken(token: string): DemoPayload | null {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return null;
    const payload = JSON.parse(atob(parts[1].replace(/-/g, "+").replace(/_/g, "/")));
    if (!payload.name || !payload.school_org) return null;
    if (payload.exp && payload.exp < Date.now() / 1000) return null;
    return payload as DemoPayload;
  } catch {
    return null;
  }
}

interface Props {
  token: string | null;
  accentColor?: "violet" | "blue" | "green";
}

export function DemoTourBanner({ token, accentColor = "violet" }: Props) {
  const [payload, setPayload] = useState<DemoPayload | null>(null);

  useEffect(() => {
    if (!token) return;
    setPayload(decodeToken(token));
  }, [token]);

  if (!payload) return null;

  const colors = {
    violet: {
      bg: "bg-violet-50",
      border: "border-violet-200",
      icon: "text-violet-500",
      heading: "text-violet-900",
      body: "text-violet-700",
    },
    blue: {
      bg: "bg-blue-50",
      border: "border-blue-200",
      icon: "text-blue-500",
      heading: "text-blue-900",
      body: "text-blue-700",
    },
    green: {
      bg: "bg-green-50",
      border: "border-green-200",
      icon: "text-green-500",
      heading: "text-green-900",
      body: "text-green-700",
    },
  }[accentColor];

  return (
    <div
      className={`mx-auto max-w-3xl px-6 pt-6`}
      role="status"
      aria-label="Personalised demo tour"
    >
      <div
        className={`flex items-start gap-3 rounded-xl border ${colors.border} ${colors.bg} px-5 py-4`}
      >
        <Sparkles className={`mt-0.5 h-5 w-5 shrink-0 ${colors.icon}`} aria-hidden />
        <div>
          <p className={`text-sm font-semibold ${colors.heading}`}>
            Welcome, {payload.name} from {payload.school_org}
          </p>
          <p className={`mt-0.5 text-xs ${colors.body}`}>
            This is your personalised StudyBuddy demo tour. Take as long as you need.
          </p>
        </div>
      </div>
    </div>
  );
}
