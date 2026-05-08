import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { AbsoluteFill } from "remotion";
import { PAI_THEME } from "../theme";
import { ConfettiBurst } from "../components/ConfettiBurst";
import { SceneFrame } from "../components/SceneFrame";

/**
 * Slide 11 — finish-strong moment: streak counter ticks up.
 *
 * Aditi finishes her lesson. The streak counter ticks 7 → 8 with a
 * brief confetti burst. Same kinetic move as the student-story slide 9,
 * but lower count + chemistry tile pinned in the background.
 */
export const Slide11_StreakAccessibility: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const cardSpring = spring({
    frame,
    fps,
    config: PAI_THEME.animation.springDefault,
    durationInFrames: 30,
  });

  const count = frame < 120 ? 7 : 8;
  const tickPulse = interpolate(frame, [120, 130, 150], [1, 1.3, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <SceneFrame
      slideNumber={11}
      totalSlides={12}
      audioFile="slide-11.wav"
      caption="She finishes the unit. Eight nights of chemistry in a row — the streak counter knows."
    >
      <AbsoluteFill
        style={{
          alignItems: "center",
          justifyContent: "center",
          flexDirection: "column",
          gap: 30,
        }}
      >
        <div
          style={{
            transform: `scale(${interpolate(cardSpring, [0, 1], [0.85, 1])})`,
            opacity: cardSpring,
            padding: "60px 100px",
            backgroundColor: PAI_THEME.colors.backgroundAlt,
            borderRadius: 24,
            border: `2px solid ${PAI_THEME.colors.warning}`,
            boxShadow: `0 0 80px ${PAI_THEME.colors.warning}55`,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 20,
          }}
        >
          <span style={{ fontSize: 80 }}>🔥</span>
          <span
            style={{
              fontSize: 192,
              color: PAI_THEME.colors.warning,
              fontWeight: 800,
              fontFamily: PAI_THEME.typography.fontFamilyMono,
              transform: `scale(${tickPulse})`,
            }}
          >
            {count}
          </span>
          <span
            style={{
              color: PAI_THEME.colors.text,
              fontSize: 32,
              fontWeight: 600,
              fontFamily: PAI_THEME.typography.fontFamily,
            }}
          >
            night streak
          </span>
        </div>

        <ConfettiBurst at={125} count={28} />
      </AbsoluteFill>
    </SceneFrame>
  );
};
