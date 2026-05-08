import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { PAI_THEME } from "../theme";
import { SceneFrame } from "../components/SceneFrame";

/**
 * Slide 8 — "Tutorial section for the stuck"
 *
 * Visual: a tutorial step-by-step solution appears. Each algebra step
 * lights up sequentially as it lands. At the end, a "common mistakes"
 * callout slides in.
 */
export const Slide08_TutorialSection: React.FC = () => {
  const frame = useCurrentFrame();

  const steps = [
    { equation: "v = v₀ + at", reason: "Kinematic equation 1" },
    { equation: "0 = 25 + a(5)", reason: "Substitute v=0, v₀=25 m/s, t=5 s" },
    { equation: "a = -5 m/s²", reason: "Solve for a" },
  ];

  return (
    <SceneFrame
      slideNumber={8}
      totalSlides={12}
      audioFile="slide-08.wav"
      caption="For students stuck on motion graphs — a tutorial section. Step-by-step. Common mistakes called out by name."
    >
      <AbsoluteFill
        style={{
          alignItems: "center",
          justifyContent: "center",
          flexDirection: "column",
          gap: 28,
        }}
      >
        <h2
          style={{
            margin: 0,
            color: PAI_THEME.colors.text,
            fontSize: 48,
            fontWeight: 700,
            fontFamily: PAI_THEME.typography.fontFamily,
            opacity: interpolate(frame, [0, 24], [0, 1], {
              extrapolateRight: "clamp",
            }),
          }}
        >
          Tutorial — solve step by step
        </h2>

        <div
          style={{
            width: 1100,
            backgroundColor: PAI_THEME.colors.paperGround,
            borderRadius: 16,
            padding: "40px 60px",
            display: "flex",
            flexDirection: "column",
            gap: 22,
          }}
        >
          {steps.map((step, i) => {
            const stepStart = 60 + i * 80;
            const stepOpacity = interpolate(frame, [stepStart, stepStart + 30], [0, 1], {
              extrapolateRight: "clamp",
            });
            const highlightFade = interpolate(frame, [stepStart, stepStart + 24, stepStart + 90], [0, 0.4, 0], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            });
            return (
              <div
                key={i}
                style={{
                  opacity: stepOpacity,
                  display: "flex",
                  alignItems: "baseline",
                  gap: 32,
                  padding: 16,
                  borderRadius: 8,
                  backgroundColor: `${PAI_THEME.colors.accent}${Math.floor(highlightFade * 255)
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
                    minWidth: 50,
                  }}
                >
                  {i + 1}.
                </span>
                <span
                  style={{
                    color: PAI_THEME.colors.background,
                    fontSize: 38,
                    fontWeight: 700,
                    fontFamily: PAI_THEME.typography.fontFamilyMono,
                    minWidth: 360,
                  }}
                >
                  {step.equation}
                </span>
                <span
                  style={{
                    color: PAI_THEME.colors.accentDark,
                    fontSize: 24,
                    fontFamily: PAI_THEME.typography.fontFamily,
                    fontStyle: "italic",
                  }}
                >
                  ← {step.reason}
                </span>
              </div>
            );
          })}

          {/* Common mistakes callout */}
          <div
            style={{
              marginTop: 16,
              padding: 24,
              backgroundColor: `${PAI_THEME.colors.warning}33`,
              borderLeft: `5px solid ${PAI_THEME.colors.warning}`,
              borderRadius: 8,
              opacity: interpolate(frame, [330, 360], [0, 1], {
                extrapolateRight: "clamp",
              }),
            }}
          >
            <p
              style={{
                margin: "0 0 8px 0",
                color: PAI_THEME.colors.warning,
                fontSize: 18,
                fontWeight: 700,
                letterSpacing: 1.2,
                textTransform: "uppercase",
                fontFamily: PAI_THEME.typography.fontFamilyMono,
              }}
            >
              Common mistakes
            </p>
            <p
              style={{
                margin: 0,
                color: PAI_THEME.colors.background,
                fontSize: 22,
                fontFamily: PAI_THEME.typography.fontFamily,
              }}
            >
              Forgetting that deceleration is negative. Mixing up t and v in
              the kinematic equation.
            </p>
          </div>
        </div>
      </AbsoluteFill>
    </SceneFrame>
  );
};
