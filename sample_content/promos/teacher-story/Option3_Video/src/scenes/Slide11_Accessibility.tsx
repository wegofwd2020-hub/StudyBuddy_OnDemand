import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { PAI_THEME } from "../theme";
import { CursorTrace } from "../components/CursorTrace";
import { SceneFrame } from "../components/SceneFrame";

/**
 * Slide 11 — "Accessible by default"
 *
 * Visual: a sample paragraph renders in standard typography. The
 * cursor moves to a top-right "eye" icon, clicks, and the paragraph
 * reflows with wider letter-spacing and OpenDyslexic-styled emphasis
 * on the first letter of each word (a stand-in for the real font
 * swap, which only exists in the production app).
 */
export const Slide11_Accessibility: React.FC = () => {
  const frame = useCurrentFrame();
  const toggleAt = 180;
  const toggleProgress = interpolate(frame, [toggleAt, toggleAt + 18], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Letter-spacing transitions from 0 to 0.08em as the toggle fires
  const letterSpacing = interpolate(toggleProgress, [0, 1], [0, 0.08]);
  const lineHeight = interpolate(toggleProgress, [0, 1], [1.5, 1.95]);

  return (
    <SceneFrame
      slideNumber={11}
      totalSlides={12}
      audioFile="slide-11.mp3"
      caption="Accessibility is one toggle. Setting follows the student across every page, every device."
    >
      <AbsoluteFill
        style={{
          alignItems: "center",
          justifyContent: "center",
          flexDirection: "column",
          gap: 30,
        }}
      >
        {/* Sample paragraph card */}
        <div
          style={{
            width: 1100,
            padding: 60,
            backgroundColor: PAI_THEME.colors.paperGround,
            borderRadius: 16,
            position: "relative",
          }}
        >
          {/* Accessibility eye icon (top-right of card) */}
          <div
            style={{
              position: "absolute",
              top: 20,
              right: 20,
              width: 56,
              height: 56,
              backgroundColor: interpolate(toggleProgress, [0, 1], [0.0, 1.0]) > 0.5
                ? PAI_THEME.colors.accent
                : PAI_THEME.colors.backgroundAlt,
              borderRadius: "50%",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: PAI_THEME.colors.text,
              fontSize: 28,
              transition: "background-color 0.3s",
            }}
          >
            👁
          </div>

          <p
            style={{
              margin: 0,
              color: PAI_THEME.colors.background,
              fontSize: 32,
              fontFamily: PAI_THEME.typography.fontFamily,
              letterSpacing: `${letterSpacing}em`,
              lineHeight,
              transition: "letter-spacing 0.3s, line-height 0.3s",
            }}
          >
            When a body changes its motion, an unbalanced force is acting
            on it. The acceleration is proportional to the net force and
            inversely proportional to the mass.
          </p>

          <p
            style={{
              marginTop: 20,
              color: PAI_THEME.colors.accentDark,
              fontSize: 18,
              fontFamily: PAI_THEME.typography.fontFamilyMono,
              opacity: toggleProgress,
              fontWeight: 700,
              letterSpacing: 1.4,
              textTransform: "uppercase",
            }}
          >
            ▸ OpenDyslexic mode — extra letter-spacing, broader line-height
          </p>
        </div>

        {/* Cursor moves to the eye icon and clicks */}
        <CursorTrace
          path={[
            { x: 200, y: 800, atFrame: 80 },
            { x: 1340, y: 250, atFrame: 170 },
          ]}
          clickAt={toggleAt}
        />
      </AbsoluteFill>
    </SceneFrame>
  );
};
