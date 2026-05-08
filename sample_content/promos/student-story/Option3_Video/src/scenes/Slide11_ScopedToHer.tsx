import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { PAI_THEME } from "../theme";
import { StreamMontage } from "../components/StreamMontage";
import { SceneFrame } from "../components/SceneFrame";

/**
 * Slide 11 — "Scoped to her"
 *
 * Visual: rapid-fire montage emphasising that the same engine renders
 * different content for different students. Maya gets G11 Science.
 * Her cousin gets G11 Commerce. Her sister gets G8 STEM. Same engine,
 * different output.
 */
export const Slide11_ScopedToHer: React.FC = () => {
  const frame = useCurrentFrame();
  const headlineOpacity = interpolate(frame, [0, 24], [0, 1], {
    extrapolateRight: "clamp",
  });
  const headlineFade = interpolate(frame, [60, 90], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <SceneFrame
      slideNumber={11}
      totalSlides={12}
      audioFile="slide-11.wav"
      caption="Maya gets G11 Science. Her cousin, G11 Commerce. Her sister, G8 STEM. Same engine — different lesson, every time."
    >
      <AbsoluteFill>
        <div
          style={{
            position: "absolute",
            top: 130,
            left: 0,
            right: 0,
            textAlign: "center",
            opacity: headlineOpacity * headlineFade,
          }}
        >
          <p
            style={{
              margin: 0,
              color: PAI_THEME.colors.text,
              fontSize: 44,
              fontWeight: 700,
              fontFamily: PAI_THEME.typography.fontFamily,
            }}
          >
            Scoped to her — every time
          </p>
        </div>

        <StreamMontage
          appearAt={75}
          streams={[
            { label: "Maya · G11 Science", color: PAI_THEME.colors.dim2 },
            { label: "Cousin · G11 Commerce", color: PAI_THEME.colors.dim4 },
            { label: "Sister · G8 STEM", color: PAI_THEME.colors.dim3 },
          ]}
        />
      </AbsoluteFill>
    </SceneFrame>
  );
};
