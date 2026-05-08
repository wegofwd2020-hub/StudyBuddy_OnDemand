import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { PAI_THEME } from "../theme";
import { TypeInText } from "../components/TypeInText";
import { SceneFrame } from "../components/SceneFrame";

/**
 * Slide 1 — title card "Inside an Alkenes Lesson"
 *
 * Cold open. Title types in. Subtitle fades in below. Same kinetic
 * vocabulary as the existing teacher-story / student-story title cards
 * so the three videos read as a series.
 */
export const Slide01_TitleCard: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const titleScale = spring({ frame, fps, config: PAI_THEME.animation.springDefault });
  const subtitleOpacity = interpolate(frame, [120, 180], [0, 1], { extrapolateRight: "clamp" });

  return (
    <SceneFrame
      slideNumber={1}
      totalSlides={12}
      audioFile="slide-01.wav"
      caption="Inside a Grade 11 Chemistry lesson — alkenes, the building blocks of plastics, fuels, and a thousand reactions."
    >
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", flexDirection: "column", gap: 24 }}>
        <div
          style={{
            transform: `scale(${interpolate(titleScale, [0, 1], [0.85, 1])})`,
            opacity: titleScale,
            color: PAI_THEME.colors.text,
            fontFamily: PAI_THEME.typography.fontFamily,
            fontSize: 96,
            fontWeight: 700,
            letterSpacing: -1.5,
            textAlign: "center",
          }}
        >
          <TypeInText text="Inside an Alkenes Lesson" cps={20} startAt={20} showCaret={false} />
        </div>

        <p
          style={{
            opacity: subtitleOpacity,
            color: PAI_THEME.colors.textMuted,
            fontSize: 32,
            margin: 0,
            fontFamily: PAI_THEME.typography.fontFamily,
            maxWidth: 1100,
            textAlign: "center",
            lineHeight: 1.4,
          }}
        >
          Aditi · Grade 11 · Science · Chemistry stream — what she sees on her laptop tonight.
        </p>
      </AbsoluteFill>
    </SceneFrame>
  );
};
