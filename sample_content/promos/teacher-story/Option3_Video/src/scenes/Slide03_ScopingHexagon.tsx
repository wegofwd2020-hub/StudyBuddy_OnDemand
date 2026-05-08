import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { PAI_THEME } from "../theme";
import { ScopingHexagon } from "../components/ScopingHexagon";
import { SceneFrame } from "../components/SceneFrame";

/**
 * Slide 3 — Scoping hexagon centerpiece
 *
 * Visual: the six query dimensions orbit toward a glowing centroid and
 * lock into a hexagonal arrangement. Each label appears in turn, timed
 * to the narration. After the hexagon locks, an "engine" tag appears
 * below the centroid.
 *
 * This is the v2 storyboard's centerpiece kinetic moment.
 */
export const Slide03_ScopingHexagon: React.FC = () => {
  const frame = useCurrentFrame();
  const headlineOpacity = interpolate(frame, [0, 24], [0, 1], {
    extrapolateRight: "clamp",
  });
  const engineLabelOpacity = interpolate(frame, [240, 280], [0, 1], {
    extrapolateRight: "clamp",
  });

  return (
    <SceneFrame
      slideNumber={3}
      totalSlides={12}
      audioFile="slide-03.mp3"
      caption="The system scopes the query against six dimensions — that tuple makes the lesson hers, not generic."
    >
      <AbsoluteFill>
        <ScopingHexagon />

        {/* Headline above the hexagon */}
        <div
          style={{
            position: "absolute",
            top: 110,
            left: 0,
            right: 0,
            textAlign: "center",
            opacity: headlineOpacity,
          }}
        >
          <p
            style={{
              margin: 0,
              color: PAI_THEME.colors.text,
              fontSize: 40,
              fontWeight: 600,
              fontFamily: PAI_THEME.typography.fontFamily,
            }}
          >
            Scoped retrieval — six dimensions
          </p>
        </div>

        {/* Engine label below the centroid (after lock) */}
        <div
          style={{
            position: "absolute",
            top: "calc(50% + 90px)",
            left: 0,
            right: 0,
            textAlign: "center",
            opacity: engineLabelOpacity,
          }}
        >
          <p
            style={{
              margin: 0,
              color: PAI_THEME.colors.accentLight,
              fontSize: 24,
              fontWeight: 600,
              fontFamily: PAI_THEME.typography.fontFamilyMono,
              letterSpacing: 2,
              textTransform: "uppercase",
            }}
          >
            ▸ Studybuddy engine
          </p>
        </div>
      </AbsoluteFill>
    </SceneFrame>
  );
};
