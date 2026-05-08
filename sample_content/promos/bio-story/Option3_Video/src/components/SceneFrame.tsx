import React from "react";
import { AbsoluteFill, Audio, interpolate, useCurrentFrame } from "remotion";
import { staticFile } from "remotion";
import { PAI_THEME } from "../theme";

/**
 * <SceneFrame> — shared wrapper for every scene.
 *
 * Establishes:
 *   - Background colour
 *   - Slide-number badge (top-left)
 *   - Per-slide narration audio (mp3 from staticFile path)
 *   - Lower-third caption (for muted-autoplay accessibility)
 *   - Brand mark (top-right)
 *
 * Each scene component composes one or more kinetic visual moves
 * (TypeInText, ScopingHexagon, SlideInPanel, etc.) inside this frame.
 *
 * @param slideNumber  1-indexed slide number, displayed in the corner badge.
 * @param totalSlides  Total slides in this story (for the badge denominator).
 * @param caption      Lower-third caption text (mirrors the narration).
 * @param audioFile    Filename in audio/ directory (e.g. "slide-01.mp3").
 *                     If undefined, the scene renders silent (useful during
 *                     development before Polly has been run).
 */
export const SceneFrame: React.FC<{
  slideNumber: number;
  totalSlides: number;
  caption: string;
  audioFile?: string;
  children: React.ReactNode;
}> = ({ slideNumber, totalSlides, caption, audioFile, children }) => {
  const frame = useCurrentFrame();
  const captionOpacity = interpolate(
    frame,
    [15, 30, 450, 470],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  return (
    <AbsoluteFill style={{ backgroundColor: PAI_THEME.colors.background }}>
      {audioFile && <Audio src={staticFile(`audio/${audioFile}`)} />}

      {/* The scene content */}
      {children}

      {/* Top-left slide badge */}
      <div
        style={{
          position: "absolute",
          top: 30,
          left: 40,
          padding: "6px 14px",
          backgroundColor: PAI_THEME.colors.backgroundAlt,
          color: PAI_THEME.colors.textMuted,
          fontSize: 18,
          borderRadius: 999,
          fontFamily: PAI_THEME.typography.fontFamilyMono,
          letterSpacing: 1.5,
        }}
      >
        {String(slideNumber).padStart(2, "0")} / {String(totalSlides).padStart(2, "0")}
      </div>

      {/* Top-right brand mark */}
      <div
        style={{
          position: "absolute",
          top: 30,
          right: 40,
          color: PAI_THEME.colors.accentLight,
          fontSize: 22,
          fontWeight: 700,
          fontFamily: PAI_THEME.typography.fontFamily,
          letterSpacing: 0.5,
        }}
      >
        StudyBuddy
      </div>

      {/* Lower-third caption (accessibility + muted autoplay) */}
      <div
        style={{
          position: "absolute",
          bottom: 60,
          left: "10%",
          right: "10%",
          padding: "16px 28px",
          backgroundColor: "rgba(15, 23, 42, 0.85)",
          borderRadius: 10,
          border: `1px solid ${PAI_THEME.colors.textDark}`,
          opacity: captionOpacity,
        }}
      >
        <p
          style={{
            margin: 0,
            color: PAI_THEME.colors.text,
            fontFamily: PAI_THEME.typography.fontFamily,
            fontSize: 26,
            lineHeight: 1.4,
            textAlign: "center",
          }}
        >
          {caption}
        </p>
      </div>
    </AbsoluteFill>
  );
};
