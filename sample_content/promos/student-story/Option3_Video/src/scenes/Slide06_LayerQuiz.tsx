import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { PAI_THEME } from "../theme";
import { SlideInPanel } from "../components/SlideInPanel";
import { SceneFrame } from "../components/SceneFrame";

/**
 * Slide 6 — Layer 4: QUIZ
 *
 * Visual: layer indicator advances. A quiz card appears. The student
 * picks a wrong answer first (B), gets a friendly explanation; then
 * picks the right answer (D), which gets a green ring.
 */
const LAYERS = ["TEXT", "IMAGES", "ANIMATION", "QUIZ", "TUTORIAL"];

const LayerStackIndicator: React.FC<{ active: number }> = ({ active }) => (
  <div
    style={{
      width: 360,
      display: "flex",
      flexDirection: "column",
      gap: 10,
      fontFamily: PAI_THEME.typography.fontFamilyMono,
    }}
  >
    {LAYERS.map((label, i) => {
      const isActive = i === active;
      const isPast = i < active;
      return (
        <div
          key={i}
          style={{
            padding: "16px 22px",
            backgroundColor: isActive
              ? PAI_THEME.colors.accent
              : isPast
              ? PAI_THEME.colors.backgroundAlt
              : "transparent",
            border: `2px solid ${
              isActive ? PAI_THEME.colors.accentLight : PAI_THEME.colors.textDark
            }`,
            borderRadius: 8,
            color: isActive
              ? PAI_THEME.colors.text
              : isPast
              ? PAI_THEME.colors.textMuted
              : PAI_THEME.colors.textDark,
            fontSize: 22,
            fontWeight: isActive ? 700 : 500,
            display: "flex",
            justifyContent: "space-between",
            opacity: isActive ? 1 : isPast ? 0.7 : 0.4,
          }}
        >
          <span>0{i + 1}</span>
          <span>{label}</span>
        </div>
      );
    })}
  </div>
);

export const Slide06_LayerQuiz: React.FC = () => {
  const frame = useCurrentFrame();
  const cardOpacity = interpolate(frame, [0, 30], [0, 1], {
    extrapolateRight: "clamp",
  });
  const wrongRing = interpolate(frame, [120, 150], [0, 1], {
    extrapolateRight: "clamp",
  });
  const correctRing = interpolate(frame, [300, 330], [0, 1], {
    extrapolateRight: "clamp",
  });

  const options = [
    { label: "A", text: "Decreases linearly" },
    { label: "B", text: "Decreases as the square of velocity" },
    { label: "C", text: "Stays constant" },
    { label: "D", text: "Decreases linearly with time" },
  ];

  return (
    <SceneFrame
      slideNumber={6}
      totalSlides={12}
      audioFile="slide-06.mp3"
      caption="Layer four — QUIZ. Wrong answers don't get a red X. They get a two-sentence explanation."
    >
      <AbsoluteFill
        style={{
          alignItems: "center",
          justifyContent: "center",
          gap: 50,
          flexDirection: "row",
          padding: "0 80px",
        }}
      >
        <LayerStackIndicator active={3} />

        <div
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            gap: 20,
            opacity: cardOpacity,
          }}
        >
          <div
            style={{
              padding: 36,
              backgroundColor: PAI_THEME.colors.paperGround,
              borderRadius: 16,
              boxShadow: "0 30px 60px rgba(0,0,0,0.4)",
            }}
          >
            <p
              style={{
                margin: "0 0 8px 0",
                color: PAI_THEME.colors.accent,
                fontSize: 16,
                fontWeight: 700,
                letterSpacing: 1.4,
                textTransform: "uppercase",
                fontFamily: PAI_THEME.typography.fontFamilyMono,
              }}
            >
              Q4 / 8
            </p>
            <h2
              style={{
                margin: "0 0 22px 0",
                color: PAI_THEME.colors.background,
                fontSize: 30,
                fontWeight: 600,
                fontFamily: PAI_THEME.typography.fontFamily,
              }}
            >
              A car decelerates uniformly. How does its velocity change?
            </h2>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {options.map((opt, i) => {
                const isWrong = opt.label === "B";
                const isCorrect = opt.label === "D";
                const ring = isWrong
                  ? wrongRing
                  : isCorrect
                  ? correctRing
                  : 0;
                const ringColor = isWrong
                  ? PAI_THEME.colors.error
                  : isCorrect
                  ? PAI_THEME.colors.success
                  : PAI_THEME.colors.textDark;
                return (
                  <div
                    key={i}
                    style={{
                      padding: "12px 20px",
                      borderRadius: 8,
                      border: `2px solid ${
                        ring > 0 ? ringColor : PAI_THEME.colors.textDark
                      }`,
                      backgroundColor:
                        ring > 0 ? `${ringColor}22` : "transparent",
                      color: PAI_THEME.colors.background,
                      fontSize: 20,
                      fontFamily: PAI_THEME.typography.fontFamily,
                    }}
                  >
                    <strong>{opt.label}.</strong> {opt.text}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Wrong-answer feedback slides up first */}
          <SlideInPanel from="bottom" appearAt={150} distance={150}>
            <div
              style={{
                padding: 22,
                backgroundColor: `${PAI_THEME.colors.warning}33`,
                borderLeft: `5px solid ${PAI_THEME.colors.warning}`,
                borderRadius: 8,
                color: PAI_THEME.colors.text,
                fontFamily: PAI_THEME.typography.fontFamily,
                fontSize: 18,
                lineHeight: 1.5,
                opacity: interpolate(frame, [180, 280], [1, 0], {
                  extrapolateLeft: "clamp",
                  extrapolateRight: "clamp",
                }),
              }}
            >
              <strong>Not quite.</strong> The square term applies to position,
              not velocity. Try thinking about what changes uniformly.
            </div>
          </SlideInPanel>
        </div>
      </AbsoluteFill>
    </SceneFrame>
  );
};
