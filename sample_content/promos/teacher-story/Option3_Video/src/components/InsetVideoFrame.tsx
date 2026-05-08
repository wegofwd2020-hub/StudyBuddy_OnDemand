import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { PAI_THEME } from "../theme";

/**
 * <InsetVideoFrame> — chrome around an embedded video clip.
 *
 * Used in the Story A slide 6 / Story B slide 6 reveal where the
 * lesson page exposes an inline animation for motion topics. Renders
 * a "browser-window" style chrome (rounded corners, three traffic
 * lights, subtle border) wrapping the children, with a scale-in
 * entry animation.
 *
 * The actual video would be passed as a child (e.g., a still image
 * representation, or an actual <Video> element when assets are wired).
 *
 * @param appearAt    Frame to begin entry (default 0).
 * @param chromeLabel Optional URL-bar text shown in the chrome (default "demo.studybuddy.app/lesson/G11-PHYS-002").
 */
export const InsetVideoFrame: React.FC<{
  appearAt?: number;
  chromeLabel?: string;
  width?: number;
  height?: number;
  children: React.ReactNode;
}> = ({
  appearAt = 0,
  chromeLabel = "demo.studybuddy.app/lesson/G11-PHYS-002",
  width = 800,
  height = 500,
  children,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const t = spring({
    frame: frame - appearAt,
    fps,
    config: PAI_THEME.animation.springBouncy,
    durationInFrames: 35,
  });

  const scale = interpolate(t, [0, 1], [0.8, 1]);
  const opacity = interpolate(t, [0, 0.5], [0, 1], { extrapolateRight: "clamp" });

  const chromeHeight = 44;
  const innerHeight = height - chromeHeight;

  return (
    <div
      style={{
        width,
        height,
        transform: `scale(${scale})`,
        opacity,
        backgroundColor: PAI_THEME.colors.paperGround,
        borderRadius: 12,
        overflow: "hidden",
        boxShadow:
          "0 30px 60px rgba(0,0,0,0.4), 0 12px 24px rgba(0,0,0,0.25)",
        border: `1px solid ${PAI_THEME.colors.textDark}`,
      }}
    >
      {/* Browser chrome */}
      <div
        style={{
          height: chromeHeight,
          backgroundColor: PAI_THEME.colors.backgroundAlt,
          display: "flex",
          alignItems: "center",
          padding: "0 14px",
          gap: 10,
          borderBottom: `1px solid ${PAI_THEME.colors.textDark}`,
        }}
      >
        {/* Three traffic lights */}
        <div style={{ display: "flex", gap: 6 }}>
          <span
            style={{
              width: 12,
              height: 12,
              borderRadius: 999,
              backgroundColor: "#ff5f56",
            }}
          />
          <span
            style={{
              width: 12,
              height: 12,
              borderRadius: 999,
              backgroundColor: "#ffbd2e",
            }}
          />
          <span
            style={{
              width: 12,
              height: 12,
              borderRadius: 999,
              backgroundColor: "#27c93f",
            }}
          />
        </div>
        {/* URL bar */}
        <div
          style={{
            flex: 1,
            height: 24,
            backgroundColor: PAI_THEME.colors.background,
            borderRadius: 6,
            display: "flex",
            alignItems: "center",
            padding: "0 12px",
            color: PAI_THEME.colors.textMuted,
            fontSize: 14,
            fontFamily: PAI_THEME.typography.fontFamilyMono,
          }}
        >
          🔒 {chromeLabel}
        </div>
      </div>

      {/* Inner content area */}
      <div
        style={{
          width,
          height: innerHeight,
          backgroundColor: "#000",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: PAI_THEME.colors.text,
        }}
      >
        {children}
      </div>
    </div>
  );
};
