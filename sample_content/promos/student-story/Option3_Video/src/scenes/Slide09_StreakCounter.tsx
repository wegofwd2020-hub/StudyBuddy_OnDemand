import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { PAI_THEME } from "../theme";
import { ConfettiBurst } from "../components/ConfettiBurst";
import { SceneFrame } from "../components/SceneFrame";

/**
 * Slide 9 — "12-day streak — confetti burst"
 *
 * Visual: a streak-counter card. The number ticks 11 → 12, the card
 * pulses, and a single confetti burst fires from the centroid. This
 * is the only confetti moment in either video — used scarcely on
 * purpose so it lands.
 */
export const Slide09_StreakCounter: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Card spring-in
  const cardSpring = spring({
    frame,
    fps,
    config: PAI_THEME.animation.springDefault,
    durationInFrames: 30,
  });

  // Streak count ticks 11 → 12 at frame 120
  const count = frame < 120 ? 11 : 12;
  const tickPulse = interpolate(frame, [120, 130, 150], [1, 1.3, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <SceneFrame
      slideNumber={9}
      totalSlides={12}
      audioFile="slide-09.mp3"
      caption="Twelve nights in a row. The streak counter knows. So does the encouragement nudge — but only when it's earned."
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
              transition: "transform 0.2s",
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

        <ConfettiBurst at={125} count={32} />
      </AbsoluteFill>
    </SceneFrame>
  );
};
