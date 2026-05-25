"use client";

import Image from "next/image";
import { useEffect, useState } from "react";
import { useDyslexia } from "@/lib/hooks/useDyslexia";
import { Eye } from "lucide-react";
import { cn } from "@/lib/utils";
import { CurriculumMenu } from "@/components/layout/CurriculumMenu";
import { AccountMenu } from "@/components/layout/AccountMenu";

const PORTAL_ICONS = {
  public: { src: "/assets/home_banner.png", alt: "StudyBuddy" },
  student: { src: "/assets/books.png", alt: "Student Portal" },
  school: { src: "/assets/banyan_tree.png", alt: "School Portal" },
  admin: { src: "/assets/peeple.png", alt: "Admin Console" },
} as const;

export function PortalHeader({
  portal,
  userName,
}: {
  portal: keyof typeof PORTAL_ICONS;
  userName?: string;
}) {
  // Start null so the server renders nothing — avoids a locale-format mismatch
  // between Node.js (server) and the browser (client) which causes hydration errors.
  // The clock appears after the first client-side effect and ticks every minute.
  const [now, setNow] = useState<Date | null>(null);
  const { enabled: dyslexic, toggle: toggleDyslexic } = useDyslexia();

  useEffect(() => {
    setNow(new Date());
    const id = setInterval(() => setNow(new Date()), 60_000);
    return () => clearInterval(id);
  }, []);

  // Alt+D global keyboard shortcut for the dyslexia toggle.
  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (e.altKey && e.key.toLowerCase() === "d") {
        e.preventDefault();
        toggleDyslexic();
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [toggleDyslexic]);

  const icon = PORTAL_ICONS[portal];

  return (
    <div className="flex min-h-[52px] items-center justify-between border-b border-gray-100 bg-white px-4 py-2 shadow-sm">
      {/* Left: small portal icon */}
      <div className="relative h-10 w-16 flex-shrink-0">
        <Image
          src={icon.src}
          alt={icon.alt}
          fill
          className="object-contain object-left"
        />
      </div>

      {/* Right: curriculum menu (school) + accessibility toggle + username + live datetime */}
      <div className="flex items-center gap-3">
        {/* Curriculum Management dropdown — renders only for capability holders (issue #358) */}
        {portal === "school" && <CurriculumMenu />}
        {/* Dyslexia-friendly font toggle — accessible from topbar (Rule 18) */}
        <button
          onClick={() => toggleDyslexic()}
          aria-pressed={dyslexic}
          aria-label={
            dyslexic
              ? "Disable dyslexia-friendly font (Alt+D)"
              : "Enable dyslexia-friendly font (Alt+D)"
          }
          title={dyslexic ? "Dyslexia font: on (Alt+D)" : "Dyslexia font: off (Alt+D)"}
          className={cn(
            "flex h-7 w-7 items-center justify-center rounded-md border transition-colors",
            dyslexic
              ? "border-blue-500 bg-blue-50 text-blue-600"
              : "border-gray-200 text-gray-400 hover:border-gray-400 hover:text-gray-600",
          )}
        >
          <Eye className="h-4 w-4" aria-hidden />
        </button>

        {/* School portal: username is the account-menu trigger (config + sign out
            moved off the left rail — issue #367 AP-4). Other portals keep the
            static username display. */}
        {portal === "school" ? (
          <div className="flex items-center gap-3">
            <AccountMenu userName={userName} />
            {now && (
              <span className="hidden whitespace-nowrap text-sm text-gray-500 tabular-nums sm:inline">
                {now.toLocaleDateString()}{" "}
                {now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
              </span>
            )}
          </div>
        ) : (
          <div className="flex flex-col items-end text-sm">
            {userName && (
              <span className="max-w-[200px] truncate font-medium text-gray-700">
                {userName}
              </span>
            )}
            {now && (
              <span className="whitespace-nowrap text-gray-500 tabular-nums">
                {now.toLocaleDateString()}{" "}
                {now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
