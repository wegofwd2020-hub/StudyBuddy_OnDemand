import React from "react";

/**
 * <TutorialPage> — pixel-faithful replica of `web/components/content/TutorialRenderer.tsx`.
 *
 * Mirrors the signature collapsible-disclosure pattern:
 *   - 2xl bold gray-900 H1 with "Collapse all" / "Expand all" toggle
 *   - Per section: stone-50 rounded card, gray-300 border, shadow-md
 *     - Header row: section title + chevron-down (rotated when open)
 *     - Open body: SBMarkdown → here we use plain pre-wrapped text
 *     - Examples callout: blue-50/blue-200, Lightbulb icon, "EXAMPLES" caption
 *     - Practice question callout: purple-50/purple-200, ?-icon, "PRACTICE QUESTION"
 *   - Common mistakes aside: amber-50/amber-300, AlertTriangle icon
 *
 * Props mirror the TutorialContent shape (sections + common_mistakes).
 * Each section's `open` flag is controlled per slide so we can animate
 * the disclosure expansion mid-scene.
 */
const TUT_TOKENS = {
  bgStone50: "#fafaf9",
  bgStone100: "#f5f5f4",
  borderGray300: "#d1d5db",
  borderGray200: "#e5e7eb",
  textGray900: "#111827",
  textGray500: "#6b7280",
  textGray800: "#1f2937",
  textGray700: "#374151",

  blue50: "#eff6ff",
  blue200: "#bfdbfe",
  blue600: "#2563eb",
  blue700: "#1d4ed8",
  blue900: "#1e3a8a",

  purple50: "#faf5ff",
  purple200: "#e9d5ff",
  purple600: "#9333ea",
  purple700: "#7e22ce",
  purple900: "#581c87",

  amber50: "#fffbeb",
  amber300: "#fcd34d",
  amber600: "#d97706",
  amber800: "#92400e",
  amber900: "#78350f",
} as const;

export interface TutorialSection {
  title: string;
  content: string;
  examples?: string[];
  practiceQuestion?: string;
}

export const TutorialPage: React.FC<{
  title: string;
  sections: Array<TutorialSection & { open?: boolean }>;
  commonMistakes: string[];
}> = ({ title, sections, commonMistakes }) => {
  return (
    <article style={{ maxWidth: 920, margin: "0 auto", display: "flex", flexDirection: "column", gap: 22 }}>
      {/* Title row */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 16 }}>
        <h1
          style={{
            margin: 0,
            fontSize: 32,
            fontWeight: 700,
            color: TUT_TOKENS.textGray900,
            letterSpacing: -0.5,
          }}
        >
          {title}
        </h1>
        <div
          style={{
            border: `1px solid ${TUT_TOKENS.borderGray200}`,
            padding: "5px 11px",
            fontSize: 12,
            fontWeight: 500,
            color: TUT_TOKENS.textGray500,
            borderRadius: 6,
            flexShrink: 0,
          }}
        >
          Expand all
        </div>
      </div>

      {/* Sections */}
      <ol style={{ margin: 0, padding: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: 12 }}>
        {sections.map((section, i) => (
          <li
            key={i}
            style={{
              backgroundColor: TUT_TOKENS.bgStone50,
              border: `1px solid ${TUT_TOKENS.borderGray300}`,
              borderRadius: 8,
              boxShadow: "0 4px 6px -1px rgba(0,0,0,0.10), 0 2px 4px -2px rgba(0,0,0,0.08)",
              overflow: "hidden",
            }}
          >
            {/* Header */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "14px 18px",
                gap: 12,
                backgroundColor: section.open ? TUT_TOKENS.bgStone100 : TUT_TOKENS.bgStone50,
              }}
            >
              <h3
                style={{
                  margin: 0,
                  fontSize: 17,
                  fontWeight: 600,
                  color: TUT_TOKENS.textGray900,
                }}
              >
                {section.title}
              </h3>
              <span
                style={{
                  fontSize: 16,
                  color: TUT_TOKENS.textGray500,
                  transform: section.open ? "rotate(180deg)" : "rotate(0deg)",
                  transition: "transform 150ms",
                }}
              >
                ⌄
              </span>
            </div>

            {/* Body (when open) */}
            {section.open && (
              <div
                style={{
                  borderTop: `1px solid ${TUT_TOKENS.borderGray200}`,
                  backgroundColor: TUT_TOKENS.bgStone50,
                  padding: 20,
                  display: "flex",
                  flexDirection: "column",
                  gap: 16,
                }}
              >
                <p
                  style={{
                    margin: 0,
                    fontSize: 15,
                    color: TUT_TOKENS.textGray800,
                    lineHeight: 1.65,
                    whiteSpace: "pre-wrap",
                  }}
                >
                  {section.content}
                </p>

                {section.examples && section.examples.length > 0 && (
                  <div
                    style={{
                      backgroundColor: TUT_TOKENS.blue50,
                      border: `1px solid ${TUT_TOKENS.blue200}`,
                      borderRadius: 6,
                      padding: 12,
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 6,
                        marginBottom: 8,
                      }}
                    >
                      <span style={{ color: TUT_TOKENS.blue600, fontSize: 14 }}>💡</span>
                      <span
                        style={{
                          fontSize: 11,
                          fontWeight: 700,
                          color: TUT_TOKENS.blue700,
                          letterSpacing: 1.2,
                          textTransform: "uppercase",
                        }}
                      >
                        Examples
                      </span>
                    </div>
                    <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13.5, color: TUT_TOKENS.blue900 }}>
                      {section.examples.map((ex, ei) => (
                        <li key={ei} style={{ marginBottom: 4, lineHeight: 1.55 }}>
                          {ex}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {section.practiceQuestion && (
                  <div
                    style={{
                      backgroundColor: TUT_TOKENS.purple50,
                      border: `1px solid ${TUT_TOKENS.purple200}`,
                      borderRadius: 6,
                      padding: 12,
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 6,
                        marginBottom: 8,
                      }}
                    >
                      <span style={{ color: TUT_TOKENS.purple600, fontSize: 14 }}>?</span>
                      <span
                        style={{
                          fontSize: 11,
                          fontWeight: 700,
                          color: TUT_TOKENS.purple700,
                          letterSpacing: 1.2,
                          textTransform: "uppercase",
                        }}
                      >
                        Practice Question
                      </span>
                    </div>
                    <p style={{ margin: 0, fontSize: 13.5, color: TUT_TOKENS.purple900, lineHeight: 1.55 }}>
                      {section.practiceQuestion}
                    </p>
                  </div>
                )}
              </div>
            )}
          </li>
        ))}
      </ol>

      {/* Common mistakes */}
      {commonMistakes.length > 0 && (
        <aside
          style={{
            backgroundColor: TUT_TOKENS.amber50,
            border: `1px solid ${TUT_TOKENS.amber300}`,
            borderRadius: 8,
            padding: 16,
            boxShadow: "0 1px 2px rgba(0,0,0,0.04)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
            <span style={{ color: TUT_TOKENS.amber600, fontSize: 16 }}>⚠</span>
            <h2
              style={{
                margin: 0,
                fontSize: 14,
                fontWeight: 600,
                color: TUT_TOKENS.amber800,
              }}
            >
              Common mistakes
            </h2>
          </div>
          <ul style={{ margin: 0, paddingLeft: 20, fontSize: 14, color: TUT_TOKENS.amber900, lineHeight: 1.6 }}>
            {commonMistakes.map((m, i) => (
              <li key={i} style={{ marginBottom: 4 }}>
                {m}
              </li>
            ))}
          </ul>
        </aside>
      )}
    </article>
  );
};
