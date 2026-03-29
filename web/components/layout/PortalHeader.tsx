"use client";

import Image from "next/image";
import { useEffect, useState } from "react";

const PORTAL_ICONS = {
  public:  { src: "/assets/home_banner.png", alt: "StudyBuddy" },
  student: { src: "/assets/books.png",       alt: "Student Portal" },
  school:  { src: "/assets/banyan_tree.png", alt: "School Portal" },
  admin:   { src: "/assets/peeple.png",      alt: "Admin Console" },
} as const;

export function PortalHeader({
  portal,
  userName,
}: {
  portal: keyof typeof PORTAL_ICONS;
  userName?: string;
}) {
  const [now, setNow] = useState<Date | null>(() => new Date());

  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 60_000);
    return () => clearInterval(id);
  }, []);

  const icon = PORTAL_ICONS[portal];

  return (
    <div className="flex items-center justify-between px-4 py-2 bg-white border-b border-gray-100 shadow-sm min-h-[52px]">
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
          <span className="font-medium text-gray-700 truncate max-w-[180px]">
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
