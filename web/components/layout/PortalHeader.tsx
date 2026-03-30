"use client";

import Image from "next/image";
import { useEffect, useState } from "react";

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

  useEffect(() => {
    setNow(new Date());
    const id = setInterval(() => setNow(new Date()), 60_000);
    return () => clearInterval(id);
  }, []);

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

      {/* Right: username + live datetime */}
      <div className="flex items-center gap-3 text-sm text-gray-500">
        {userName && (
          <span className="max-w-[180px] truncate font-medium text-gray-700">
            {userName}
          </span>
        )}
        {now && (
          <span className="whitespace-nowrap tabular-nums">
            {now.toLocaleDateString()}{" "}
            {now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
          </span>
        )}
      </div>
    </div>
  );
}
