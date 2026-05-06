"use client";

import type { ReactNode } from "react";
import { useSubjectPalette } from "@/lib/theme/SchoolThemeContext";

interface AisleProps {
  subject: string;
  ariaId: string;
  children: ReactNode;
  /** Override the subject-palette accent for the heading border + ink color. */
  headingAccent?: string;
}

export function Aisle({ subject, ariaId, children, headingAccent }: AisleProps) {
  // Hook must be called unconditionally; we only swap the resolved colors.
  const palette = useSubjectPalette(subject);
  const borderColor = headingAccent ?? palette.accent;
  const inkColor = headingAccent ?? palette.ink;
  return (
    <section role="region" aria-labelledby={ariaId} className="mb-8">
      <h2
        id={ariaId}
        className="mb-3 border-l-4 pl-3 text-lg font-semibold"
        style={{ borderColor, color: inkColor }}
      >
        {subject}
      </h2>
      {children}
    </section>
  );
}
