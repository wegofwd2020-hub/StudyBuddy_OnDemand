import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { PAI_THEME } from "../theme";
import { SceneFrame } from "../components/SceneFrame";

/**
 * Slide 7 — Layer 5: TUTORIAL
 *
 * Visual: layer indicator at the final slot. A tutorial step-by-step
 * solution lights up sequentially with the substitution highlighted on
 * each step.
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

export const Slide07_LayerTutorial: React.FC = () => {
  const frame = useCurrentFrame();
  const steps = [
    { equation: "v = v₀ + at", reason: "Kinematic equation 1" },
    { equation: "0 = 25 + a(5)", reason: "Sub v=0, v₀=25, t=5" },
    { equation: "a = -5 m/s²", reason: "Solve for a" },
  ];

  return (
    <SceneFrame
      slideNumber={7}
      totalSlides={12}
      audioFile="slide-07.wav"
      caption="Layer five — TUTORIAL. When the quiz says you're stuck, the lesson opens up the steps."
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
        <LayerStackIndicator active={4} />

        <div
          style={{
            flex: 1,
            backgroundColor: PAI_THEME.colors.paperGround,
            borderRadius: 16,
            padding: "40px 50px",
            display: "flex",
            flexDirection: "column",
            gap: 20,
          }}
        >
          {steps.map((step, i) => {
            const stepStart = 60 + i * 80;
            const stepOpacity = interpolate(
              frame,
              [stepStart, stepStart + 30],
              [0, 1],
              { extrapolateRight: "clamp" },
            );
            const highlightFade = interpolate(
              frame,
              [stepStart, stepStart + 24, stepStart + 90],
              [0, 0.4, 0],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
            );
            return (
              <div
                key={i}
                style={{
                  opacity: stepOpacity,
                  display: "flex",
                  alignItems: "baseline",
                  gap: 24,
                  padding: 14,
                  borderRadius: 8,
                  backgroundColor: `${PAI_THEME.colors.accent}${Math.floor(
                    highlightFade * 255,
                  )
                    .toString(16)
                    .padStart(2, "0")}`,
                }}
              >
                <span
                  style={{
                    color: PAI_THEME.colors.accent,
                    fontSize: 22,
                    fontWeight: 700,
                    fontFamily: PAI_THEME.typography.fontFamilyMono,
                    minWidth: 40,
                  }}
                >
                  {i + 1}.
                </span>
                <span
                  style={{
                    color: PAI_THEME.colors.background,
                    fontSize: 32,
                    fontWeight: 700,
                    fontFamily: PAI_THEME.typography.fontFamilyMono,
                    minWidth: 280,
                  }}
                >
                  {step.equation}
                </span>
                <span
                  style={{
                    color: PAI_THEME.colors.accentDark,
                    fontSize: 20,
                    fontFamily: PAI_THEME.typography.fontFamily,
                    fontStyle: "italic",
                  }}
                >
                  ← {step.reason}
                </span>
              </div>
            );
          })}
        </div>
      </AbsoluteFill>
    </SceneFrame>
  );
};
