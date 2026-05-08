import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { PAI_THEME } from "../theme";
import { SceneFrame } from "../components/SceneFrame";

/**
 * Slide 12 — end slate, mirrors the existing student-story / teacher-story
 * end card so the three videos close on a consistent brand mark.
 */
export const Slide12_CallToAction: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const titleSpring = spring({ frame, fps, config: PAI_THEME.animation.springDefault, durationInFrames: 30 });
  const ctaOpacity = interpolate(frame, [60, 100], [0, 1], { extrapolateRight: "clamp" });
  const pulse = (frame % 60) / 60;
  const pulseScale = 1 + 0.05 * Math.sin(pulse * Math.PI * 2);

  return (
    <SceneFrame
      slideNumber={12}
      totalSlides={12}
      audioFile="slide-12.wav"
      caption="See a chemistry lesson for yourself at demo dot studybuddy dot app, or have your school reach out to support."
    >
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", flexDirection: "column", gap: 50 }}>
        <div
          style={{
            transform: `scale(${interpolate(titleSpring, [0, 1], [0.85, 1])})`,
            opacity: titleSpring,
            textAlign: "center",
          }}
        >
          <p
            style={{
              margin: 0,
              color: PAI_THEME.colors.accentLight,
              fontSize: 96,
              fontWeight: 800,
              fontFamily: PAI_THEME.typography.fontFamily,
              letterSpacing: -2,
            }}
          >
            StudyBuddy
          </p>
          <p
            style={{
              margin: "12px 0 0 0",
              color: PAI_THEME.colors.text,
              fontSize: 36,
              fontFamily: PAI_THEME.typography.fontFamily,
              fontStyle: "italic",
            }}
          >
            Lessons, always current.
          </p>
        </div>

        <div
          style={{
            display: "flex",
            gap: 40,
            opacity: ctaOpacity,
            transform: `scale(${pulseScale})`,
          }}
        >
          <div
            style={{
              padding: "24px 48px",
              backgroundColor: PAI_THEME.colors.accent,
              color: PAI_THEME.colors.text,
              fontSize: 28,
              fontWeight: 700,
              borderRadius: 999,
              fontFamily: PAI_THEME.typography.fontFamily,
              boxShadow: `0 12px 32px ${PAI_THEME.colors.accent}55`,
            }}
          >
            ▸ demo.studybuddy.app
          </div>
          <div
            style={{
              padding: "24px 48px",
              backgroundColor: PAI_THEME.colors.text,
              color: PAI_THEME.colors.background,
              fontSize: 28,
              fontWeight: 700,
              borderRadius: 999,
              fontFamily: PAI_THEME.typography.fontFamily,
              boxShadow: "0 12px 32px rgba(241,245,249,0.15)",
            }}
          >
            ✉ support@studybuddy.app
          </div>
        </div>
      </AbsoluteFill>
    </SceneFrame>
  );
};
