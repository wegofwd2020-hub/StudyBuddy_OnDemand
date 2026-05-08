import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { PAI_THEME } from "../theme";
import { TypeInText } from "../components/TypeInText";
import { SceneFrame } from "../components/SceneFrame";

/**
 * Slide 1 — Title card "How a Lesson Gets Built"
 *
 * Visual: Cold-open. Title types in letter-by-letter; then the subtitle
 * fades in below. The brand mark and slide badge from SceneFrame anchor
 * the layout. Caption mirrors the opening narration.
 */
export const Slide01_TitleCard: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const titleScale = spring({
    frame,
    fps,
    config: PAI_THEME.animation.springDefault,
  });

  const subtitleOpacity = interpolate(frame, [120, 180], [0, 1], {
    extrapolateRight: "clamp",
  });

  return (
    <SceneFrame
      slideNumber={1}
      totalSlides={12}
      audioFile="slide-01.mp3"
      caption="Watch a Grade 11 Physics lesson assemble itself — text, diagrams, an animation, and a quiz."
    >
      <AbsoluteFill
        style={{
          alignItems: "center",
          justifyContent: "center",
          flexDirection: "column",
          gap: 24,
        }}
      >
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
          <TypeInText
            text="How a Lesson Gets Built"
            cps={20}
            startAt={20}
            showCaret={false}
          />
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
          A Grade 11 Physics lesson — generated, current, scoped to one
          teacher's curriculum — in real time.
        </p>
      </AbsoluteFill>
    </SceneFrame>
  );
};
