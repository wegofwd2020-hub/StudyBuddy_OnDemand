import React from "react";

/**
 * <QuizPage> — pixel-faithful replica of `web/components/content/QuizPlayer.tsx`
 * in the "answering" or "reviewing" phase.
 *
 * Mirrors the real player's signature visuals:
 *   - "Question N of M" + progress dots (blue-500 done, blue-300 active, gray-100 todo)
 *   - White rounded card with subtle border + shadow-sm
 *   - lg medium gray-900 question text
 *   - Outline button options with stateful colour treatment:
 *       - selected (answering)        = blue-500 border + blue-50 bg
 *       - reviewed correct           = green-500 border + green-50 bg + check icon
 *       - reviewed selected & wrong  = red-500 border + red-50 bg + X icon
 *   - Explanation panel below (gray-50 with explanation text) when reviewing
 *   - "Submit answer" / "Next question" button bottom right
 *
 * `phase` controls which highlighting + which CTA appears.
 */
const QUIZ_TOKENS = {
  bgWhite: "#ffffff",
  borderDefault: "#e5e7eb",
  textGray900: "#111827",
  textGray500: "#6b7280",
  textGray100: "#f3f4f6",

  blue50: "#eff6ff",
  blue100: "#dbeafe",
  blue300: "#93c5fd",
  blue500: "#3b82f6",
  blue600: "#2563eb",
  blue800: "#1e40af",

  green50: "#f0fdf4",
  green500: "#22c55e",
  green600: "#16a34a",
  green800: "#166534",

  red50: "#fef2f2",
  red500: "#ef4444",
  red800: "#991b1b",

  bgGray50: "#f9fafb",
  textGray600: "#4b5563",
} as const;

export interface QuizQuestion {
  prompt: string;
  options: string[];
  correctIndex: number;
  explanation?: string;
}

export const QuizPage: React.FC<{
  question: QuizQuestion;
  questionIndex: number; // 0-based
  totalQuestions: number;
  selectedIndex: number | null;
  phase: "answering" | "reviewing";
}> = ({ question, questionIndex, totalQuestions, selectedIndex, phase }) => {
  const reviewed = phase === "reviewing";
  return (
    <div style={{ maxWidth: 820, margin: "0 auto", display: "flex", flexDirection: "column", gap: 24 }}>
      {/* Progress row */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          fontSize: 14,
          color: QUIZ_TOKENS.textGray500,
        }}
      >
        <span>
          Question {questionIndex + 1} of {totalQuestions}
        </span>
        <div style={{ display: "flex", gap: 4 }}>
          {Array.from({ length: totalQuestions }).map((_, i) => {
            const color =
              i < questionIndex
                ? QUIZ_TOKENS.blue500
                : i === questionIndex
                ? QUIZ_TOKENS.blue300
                : QUIZ_TOKENS.textGray100;
            return (
              <span
                key={i}
                style={{
                  height: 6,
                  width: 24,
                  borderRadius: 999,
                  backgroundColor: color,
                  display: "inline-block",
                }}
              />
            );
          })}
        </div>
      </div>

      {/* Question card */}
      <div
        style={{
          backgroundColor: QUIZ_TOKENS.bgWhite,
          border: `1px solid ${QUIZ_TOKENS.borderDefault}`,
          borderRadius: 12,
          padding: 32,
          boxShadow: "0 1px 2px rgba(0,0,0,0.04)",
        }}
      >
        <p
          style={{
            margin: "0 0 22px 0",
            fontSize: 22,
            fontWeight: 500,
            color: QUIZ_TOKENS.textGray900,
            lineHeight: 1.45,
          }}
        >
          {question.prompt}
        </p>

        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {question.options.map((opt, i) => {
            const isSelected = selectedIndex === i;
            const isCorrect = i === question.correctIndex;
            let border = `1px solid ${QUIZ_TOKENS.borderDefault}`;
            let bg = QUIZ_TOKENS.bgWhite;
            let color = QUIZ_TOKENS.textGray900;
            let icon: string | null = null;
            if (reviewed && isCorrect) {
              border = `1px solid ${QUIZ_TOKENS.green500}`;
              bg = QUIZ_TOKENS.green50;
              color = QUIZ_TOKENS.green800;
              icon = "✓";
            } else if (reviewed && isSelected && !isCorrect) {
              border = `1px solid ${QUIZ_TOKENS.red500}`;
              bg = QUIZ_TOKENS.red50;
              color = QUIZ_TOKENS.red800;
              icon = "✕";
            } else if (isSelected) {
              border = `1px solid ${QUIZ_TOKENS.blue500}`;
              bg = QUIZ_TOKENS.blue50;
              color = QUIZ_TOKENS.blue800;
            }
            return (
              <div
                key={i}
                style={{
                  border,
                  backgroundColor: bg,
                  color,
                  borderRadius: 8,
                  padding: "14px 18px",
                  fontSize: 16,
                  fontWeight: 500,
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  textAlign: "left",
                }}
              >
                {icon && (
                  <span style={{ fontSize: 16, flexShrink: 0 }} aria-hidden>
                    {icon}
                  </span>
                )}
                {opt}
              </div>
            );
          })}
        </div>

        {reviewed && question.explanation && (
          <div
            style={{
              marginTop: 18,
              backgroundColor: QUIZ_TOKENS.bgGray50,
              border: `1px solid ${QUIZ_TOKENS.borderDefault}`,
              borderRadius: 8,
              padding: 14,
              fontSize: 14,
              color: QUIZ_TOKENS.textGray600,
              lineHeight: 1.6,
            }}
          >
            {question.explanation}
          </div>
        )}
      </div>

      {/* CTA button */}
      <div style={{ display: "flex", justifyContent: "flex-end" }}>
        <div
          style={{
            backgroundColor: QUIZ_TOKENS.blue600,
            color: "#fff",
            padding: "10px 22px",
            borderRadius: 8,
            fontSize: 14,
            fontWeight: 600,
            opacity: phase === "answering" && selectedIndex === null ? 0.5 : 1,
          }}
        >
          {phase === "answering"
            ? "Submit answer"
            : questionIndex === totalQuestions - 1
            ? "See results"
            : "Next question"}
        </div>
      </div>
    </div>
  );
};
