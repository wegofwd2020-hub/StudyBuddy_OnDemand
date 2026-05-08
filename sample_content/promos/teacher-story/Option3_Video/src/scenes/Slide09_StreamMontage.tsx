import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { PAI_THEME } from "../theme";
import { StreamMontage } from "../components/StreamMontage";
import { SceneFrame } from "../components/SceneFrame";

/**
 * Slide 9 — "Same engine, different stream"
 *
 * Visual: rapid-fire montage of stream-specific lessons. G12 Science →
 * G11 Commerce → G8 STEM. Each flashes for 2 seconds with a stream
 * label and a placeholder content tile.
 */
export const Slide09_StreamMontage: React.FC = () => {
  const frame = useCurrentFrame();

  const headlineOpacity = interpolate(frame, [0, 24], [0, 1], {
    extrapolateRight: "clamp",
  });

  // Headline only visible at the start; the montage takes over after
  const headlineFade = interpolate(frame, [60, 90], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <SceneFrame
      slideNumber={9}
      totalSlides={12}
      audioFile="slide-09.mp3"
      caption="One engine, every audience. Same topic, regenerated for G12 Science, G11 Commerce, G8 STEM."
    >
      <AbsoluteFill>
        {/* Headline */}
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
            Same engine — every stream
          </p>
        </div>

        <StreamMontage
          appearAt={75}
          streams={[
            { label: "G12 Science", color: PAI_THEME.colors.dim2 },
            { label: "G11 Commerce", color: PAI_THEME.colors.dim4 },
            { label: "G8 STEM", color: PAI_THEME.colors.dim3 },
          ]}
        />
      </AbsoluteFill>
    </SceneFrame>
  );
};
