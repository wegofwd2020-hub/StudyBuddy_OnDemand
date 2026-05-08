import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { PAI_THEME } from "../theme";

/**
 * <SlideInPanel> — generic slide-in container with motion-blur trail.
 *
 * Used for the lesson-assembly slides (text panels, image panels,
 * video frames) in both stories. The motion-blur is approximated by
 * stacking three semi-transparent ghost panels offset along the entry
 * axis; the result reads as motion blur to the eye without requiring
 * shader work.
 *
 * @param from         "left" | "right" | "top" | "bottom" — entry direction.
 * @param distance     Pixels to travel during entry (default 600).
 * @param appearAt     Frame to begin entry within the parent sequence (default 0).
 * @param children     Panel contents.
 */
export const SlideInPanel: React.FC<{
  from?: "left" | "right" | "top" | "bottom";
  distance?: number;
  appearAt?: number;
  style?: React.CSSProperties;
  children: React.ReactNode;
}> = ({
  from = "right",
  distance = 600,
  appearAt = 0,
  style,
  children,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const t = spring({
    frame: frame - appearAt,
    fps,
    config: PAI_THEME.animation.springDefault,
    durationInFrames: 30,
  });

  const offset = interpolate(t, [0, 1], [distance, 0]);
  const direction =
    from === "left"
      ? { translateX: -offset, translateY: 0 }
      : from === "right"
      ? { translateX: offset, translateY: 0 }
      : from === "top"
      ? { translateX: 0, translateY: -offset }
      : { translateX: 0, translateY: offset };

  const opacity = interpolate(t, [0, 0.4], [0, 1], {
    extrapolateRight: "clamp",
  });

  // Motion-blur ghosts — three trailing copies at slight offsets
  const ghostOffsets = [0.3, 0.5, 0.7];
  const ghostsVisible = t < 0.85; // hide ghosts once panel is mostly settled

  return (
    <>
      {ghostsVisible &&
        ghostOffsets.map((scale, i) => (
          <div
            key={`ghost-${i}`}
            style={{
              position: "absolute",
              transform: `translate(${
                direction.translateX * scale
              }px, ${direction.translateY * scale}px)`,
              opacity: opacity * (0.15 + i * 0.05),
              filter: "blur(4px)",
              ...style,
            }}
          >
            {children}
          </div>
        ))}
      <div
        style={{
          position: "absolute",
          transform: `translate(${direction.translateX}px, ${direction.translateY}px)`,
          opacity,
          ...style,
        }}
      >
        {children}
      </div>
    </>
  );
};
