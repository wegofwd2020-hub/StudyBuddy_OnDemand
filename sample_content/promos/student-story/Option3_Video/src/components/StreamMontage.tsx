import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { PAI_THEME } from "../theme";

/**
 * <StreamMontage> — quick-cut sequence of stream-specific labels.
 *
 * Used in Story A slide 9 ("same engine, different stream") and
 * Story B slide 11 ("scoped to her"). Each stream gets a 60-frame
 * (2-second) flash with a label tag and a placeholder content tile.
 *
 * @param streams    Array of {label, color, accent} — one per cut.
 * @param appearAt   Frame to begin the montage (default 0).
 */
export const StreamMontage: React.FC<{
  streams: Array<{ label: string; color?: string }>;
  appearAt?: number;
}> = ({ streams, appearAt = 0 }) => {
  const frame = useCurrentFrame();
  const elapsed = Math.max(0, frame - appearAt);
  const flashDuration = 60; // 2 seconds at 30 fps

  // Which stream are we on? Each stream gets `flashDuration` frames.
  const activeIndex = Math.min(
    streams.length - 1,
    Math.floor(elapsed / flashDuration),
  );
  const localFrame = elapsed - activeIndex * flashDuration;

  const fadeIn = interpolate(localFrame, [0, 8], [0, 1], {
    extrapolateRight: "clamp",
  });
  const fadeOut = interpolate(
    localFrame,
    [flashDuration - 8, flashDuration],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );
  const opacity = Math.min(fadeIn, fadeOut);

  const stream = streams[activeIndex];
  const accent = stream.color ?? PAI_THEME.colors.accent;

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 32,
        opacity,
      }}
    >
      <div
        style={{
          fontSize: 64,
          fontWeight: 700,
          color: accent,
          fontFamily: PAI_THEME.typography.fontFamily,
          letterSpacing: 1.2,
        }}
      >
        {stream.label}
      </div>
      <div
        style={{
          width: 800,
          height: 360,
          backgroundColor: PAI_THEME.colors.backgroundAlt,
          borderRadius: 12,
          border: `2px solid ${accent}`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: PAI_THEME.colors.textMuted,
          fontSize: 22,
          fontStyle: "italic",
        }}
      >
        — {stream.label} lesson preview —
      </div>
    </div>
  );
};
