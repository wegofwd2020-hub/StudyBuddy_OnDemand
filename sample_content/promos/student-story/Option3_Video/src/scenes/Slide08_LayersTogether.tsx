import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { PAI_THEME } from "../theme";
import { SceneFrame } from "../components/SceneFrame";

/**
 * Slide 8 — "All five layers together"
 *
 * Visual: the five layer cards stack on screen — TEXT, IMAGES, ANIMATION,
 * QUIZ, TUTORIAL — with their preview thumbnails miniaturised. They
 * spring in from below in sequence then settle into a fan arrangement.
 * The headline reads "One lesson. Five layers."
 */
const LAYERS = [
  { name: "TEXT", color: PAI_THEME.colors.dim1, glyph: "Aa" },
  { name: "IMAGES", color: PAI_THEME.colors.dim2, glyph: "▦" },
  { name: "ANIMATION", color: PAI_THEME.colors.dim3, glyph: "▶" },
  { name: "QUIZ", color: PAI_THEME.colors.dim4, glyph: "?" },
  { name: "TUTORIAL", color: PAI_THEME.colors.dim5, glyph: "⇶" },
];

export const Slide08_LayersTogether: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const headlineOpacity = interpolate(frame, [0, 24], [0, 1], {
    extrapolateRight: "clamp",
  });

  return (
    <SceneFrame
      slideNumber={8}
      totalSlides={12}
      audioFile="slide-08.wav"
      caption="Five layers, one lesson. Read, look, watch, test, fix — all in the same place."
    >
      <AbsoluteFill
        style={{
          alignItems: "center",
          justifyContent: "center",
          flexDirection: "column",
          gap: 60,
        }}
      >
        <h2
          style={{
            margin: 0,
            color: PAI_THEME.colors.text,
            fontSize: 64,
            fontWeight: 700,
            fontFamily: PAI_THEME.typography.fontFamily,
            opacity: headlineOpacity,
          }}
        >
          One lesson. Five layers.
        </h2>

        <div
          style={{
            display: "flex",
            gap: 40,
            alignItems: "center",
          }}
        >
          {LAYERS.map((layer, i) => {
            const t = spring({
              frame: frame - (40 + i * 22),
              fps,
              config: PAI_THEME.animation.springBouncy,
              durationInFrames: 30,
            });
            const y = interpolate(t, [0, 1], [200, 0]);
            const scale = interpolate(t, [0, 1], [0.85, 1]);
            const opacity = interpolate(t, [0, 0.6], [0, 1], {
              extrapolateRight: "clamp",
            });
            return (
              <div
                key={i}
                style={{
                  width: 220,
                  height: 280,
                  backgroundColor: layer.color,
                  borderRadius: 16,
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 20,
                  transform: `translateY(${y}px) scale(${scale}) rotate(${(i - 2) * 4}deg)`,
                  opacity,
                  boxShadow: `0 20px 40px ${layer.color}66`,
                  fontFamily: PAI_THEME.typography.fontFamily,
                }}
              >
                <span style={{ fontSize: 96, color: "#0f172a", fontWeight: 700 }}>
                  {layer.glyph}
                </span>
                <span
                  style={{
                    fontSize: 22,
                    color: "#0f172a",
                    fontWeight: 700,
                    letterSpacing: 1.4,
                  }}
                >
                  {layer.name}
                </span>
              </div>
            );
          })}
        </div>
      </AbsoluteFill>
    </SceneFrame>
  );
};
