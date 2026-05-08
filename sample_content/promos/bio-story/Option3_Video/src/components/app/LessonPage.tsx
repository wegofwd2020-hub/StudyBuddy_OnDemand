import React from "react";
import { APP_TOKENS } from "./AppFrame";

/**
 * <LessonPage> — pixel-faithful replica of `web/components/content/LessonRenderer.tsx`.
 *
 * Mirrors the real renderer's signature visuals:
 *   - bg-stone-50 article card with gray-300 border + medium shadow
 *   - 2xl bold gray-900 H1
 *   - Per-section: lg semibold gray-800 H2 + leading-relaxed gray-700 body
 *   - "Key Points" callout: blue-50 bg, blue-200 border, blue-500 check icons
 *
 * Props mirror the LessonContent type (title, sections, key_points).
 *
 * `revealUpTo` (0-indexed inclusive) drives section-by-section reveal so a
 * scene can simulate the lesson loading or scrolling. Pass Infinity to
 * show everything; default = Infinity.
 */
const LESSON_TOKENS = {
  bgStone50: "#fafaf9",
  borderGray300: "#d1d5db",
  textGray900: "#111827",
  textGray800: "#1f2937",
  textGray700: "#374151",
  blue50: "#eff6ff",
  blue200: "#bfdbfe",
  blue500: "#3b82f6",
  blue800: "#1e40af",
  blue900: "#1e3a8a",
} as const;

export interface LessonSection {
  heading: string;
  body: string;
}

export const LessonPage: React.FC<{
  title: string;
  sections: LessonSection[];
  keyPoints: string[];
  revealUpTo?: number; // index of last section to render (default: all)
  showKeyPoints?: boolean; // default: true if at least all sections shown
  scrollOffsetPx?: number; // emulate vertical scroll by translating the article
}> = ({
  title,
  sections,
  keyPoints,
  revealUpTo = Infinity,
  showKeyPoints,
  scrollOffsetPx = 0,
}) => {
  const visibleSections = sections.slice(0, Math.min(sections.length, revealUpTo + 1));
  const fullyShown = visibleSections.length === sections.length;
  const renderKeyPoints =
    showKeyPoints !== undefined ? showKeyPoints : fullyShown;

  return (
    <article
      style={{
        backgroundColor: LESSON_TOKENS.bgStone50,
        border: `1px solid ${LESSON_TOKENS.borderGray300}`,
        borderRadius: 8,
        padding: 36,
        boxShadow: "0 4px 6px -1px rgba(0,0,0,0.10), 0 2px 4px -2px rgba(0,0,0,0.08)",
        transform: `translateY(${scrollOffsetPx}px)`,
        maxWidth: 920,
        margin: "0 auto",
      }}
    >
      <h1
        style={{
          margin: "0 0 24px 0",
          fontSize: 36,
          fontWeight: 700,
          color: LESSON_TOKENS.textGray900,
          letterSpacing: -0.5,
        }}
      >
        {title}
      </h1>

      {visibleSections.map((s, i) => (
        <section key={i} style={{ marginBottom: 32 }}>
          <h2
            style={{
              margin: "0 0 12px 0",
              fontSize: 22,
              fontWeight: 600,
              color: LESSON_TOKENS.textGray800,
            }}
          >
            {s.heading}
          </h2>
          <p
            style={{
              margin: 0,
              fontSize: 18,
              lineHeight: 1.7,
              color: LESSON_TOKENS.textGray700,
              whiteSpace: "pre-wrap",
            }}
          >
            {s.body}
          </p>
        </section>
      ))}

      {renderKeyPoints && keyPoints.length > 0 && (
        <div
          style={{
            marginTop: 28,
            backgroundColor: LESSON_TOKENS.blue50,
            border: `1px solid ${LESSON_TOKENS.blue200}`,
            borderRadius: 8,
            padding: 20,
            boxShadow: "0 1px 2px rgba(0,0,0,0.04)",
          }}
        >
          <h3
            style={{
              margin: "0 0 14px 0",
              fontSize: 18,
              fontWeight: 600,
              color: LESSON_TOKENS.blue800,
            }}
          >
            Key Points
          </h3>
          <ul style={{ margin: 0, padding: 0, listStyle: "none" }}>
            {keyPoints.map((p, i) => (
              <li
                key={i}
                style={{
                  marginBottom: 8,
                  display: "flex",
                  alignItems: "flex-start",
                  gap: 10,
                  fontSize: 15,
                  color: LESSON_TOKENS.blue900,
                  lineHeight: 1.5,
                }}
              >
                <span
                  style={{
                    color: LESSON_TOKENS.blue500,
                    fontSize: 16,
                    marginTop: 1,
                    flexShrink: 0,
                  }}
                >
                  ✓
                </span>
                {p}
              </li>
            ))}
          </ul>
        </div>
      )}
    </article>
  );
};

export { APP_TOKENS };
