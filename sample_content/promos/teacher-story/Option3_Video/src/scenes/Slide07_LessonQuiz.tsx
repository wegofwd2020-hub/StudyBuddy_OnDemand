import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { PAI_THEME } from "../theme";
import { SlideInPanel } from "../components/SlideInPanel";
import { SceneFrame } from "../components/SceneFrame";

/**
 * Slide 7 — "Then a quiz"
 *
 * Visual: a quiz card materialises. A correct-answer ring fades in
 * around one option, then a feedback panel slides up from below with
 * the explanation.
 */
export const Slide07_LessonQuiz: React.FC = () => {
  const frame = useCurrentFrame();
  const cardOpacity = interpolate(frame, [0, 30], [0, 1], {
    extrapolateRight: "clamp",
  });
  const correctRing = interpolate(frame, [240, 270], [0, 1], {
    extrapolateRight: "clamp",
  });

  const options = [
    { label: "A", text: "Decreases linearly", correct: false },
    { label: "B", text: "Decreases as the square of velocity", correct: false },
    { label: "C", text: "Stays constant", correct: false },
    { label: "D", text: "Decreases linearly with time", correct: true },
  ];

  return (
    <SceneFrame
      slideNumber={7}
      totalSlides={12}
      audioFile="slide-07.wav"
      caption="Then a quiz. Wrong answers don't get a red X — they get a two-sentence explanation."
    >
      <AbsoluteFill
        style={{
          alignItems: "center",
          justifyContent: "center",
          flexDirection: "column",
          gap: 40,
        }}
      >
        {/* Quiz card */}
        <div
          style={{
            width: 1100,
            padding: 48,
            backgroundColor: PAI_THEME.colors.paperGround,
            borderRadius: 16,
            opacity: cardOpacity,
            boxShadow: "0 30px 60px rgba(0,0,0,0.4)",
          }}
        >
          <p
            style={{
              margin: "0 0 12px 0",
              color: PAI_THEME.colors.accent,
              fontSize: 18,
              fontWeight: 700,
              letterSpacing: 1.4,
              textTransform: "uppercase",
              fontFamily: PAI_THEME.typography.fontFamilyMono,
            }}
          >
            Question 4 / 8
          </p>
          <h2
            style={{
              margin: "0 0 28px 0",
              color: PAI_THEME.colors.background,
              fontSize: 36,
              fontWeight: 600,
              fontFamily: PAI_THEME.typography.fontFamily,
            }}
          >
            A car decelerates uniformly. How does its velocity change with time?
          </h2>
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            {options.map((opt, i) => {
              const optionOpacity = interpolate(
                frame,
                [60 + i * 18, 90 + i * 18],
                [0, 1],
                { extrapolateRight: "clamp" },
              );
              const isCorrect = opt.correct;
              return (
                <div
                  key={i}
                  style={{
                    padding: "16px 24px",
                    borderRadius: 8,
                    border: `2px solid ${
                      isCorrect && correctRing > 0
                        ? PAI_THEME.colors.success
                        : PAI_THEME.colors.textDark
                    }`,
                    backgroundColor:
                      isCorrect && correctRing > 0
                        ? `${PAI_THEME.colors.success}22`
                        : "transparent",
                    color: PAI_THEME.colors.background,
                    fontSize: 24,
                    fontFamily: PAI_THEME.typography.fontFamily,
                    opacity: optionOpacity,
                    transition: "border-color 0.3s, background-color 0.3s",
                  }}
                >
                  <strong>{opt.label}.</strong> {opt.text}
                </div>
              );
            })}
          </div>
        </div>

        {/* Feedback panel slides up */}
        <SlideInPanel from="bottom" appearAt={300} distance={200}>
          <div
            style={{
              width: 1100,
              padding: 32,
              backgroundColor: PAI_THEME.colors.success,
              borderRadius: 12,
              color: "#0f172a",
              fontFamily: PAI_THEME.typography.fontFamily,
              fontSize: 22,
              lineHeight: 1.5,
            }}
          >
            <strong>Explanation.</strong> If acceleration is constant
            (uniform deceleration), velocity changes <em>linearly</em> with
            time. The square term applies to position, not velocity.
          </div>
        </SlideInPanel>
      </AbsoluteFill>
    </SceneFrame>
  );
};
