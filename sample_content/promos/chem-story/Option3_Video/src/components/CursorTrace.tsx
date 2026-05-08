import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { PAI_THEME } from "../theme";

/**
 * <CursorTrace> — animated cursor traversing a scripted path with
 * an optional click ripple at a specified frame.
 *
 * Used for the dyslexia-toggle moment (Story A slide 11, Story B
 * slide 10) and the "click to expand at-risk student" moment
 * (Story A slide 10). Driven by a path of {x, y, atFrame} waypoints;
 * the cursor lerps linearly between consecutive waypoints.
 *
 * @param path       Array of {x, y, atFrame} waypoints.
 * @param clickAt    Frame at which to trigger the click ripple (optional).
 */
export const CursorTrace: React.FC<{
  path: Array<{ x: number; y: number; atFrame: number }>;
  clickAt?: number;
}> = ({ path, clickAt }) => {
  const frame = useCurrentFrame();

  if (path.length === 0) return null;

  // Find the segment we're on
  let cx = path[0].x;
  let cy = path[0].y;
  for (let i = 0; i < path.length - 1; i++) {
    const a = path[i];
    const b = path[i + 1];
    if (frame >= a.atFrame && frame <= b.atFrame) {
      const t = interpolate(frame, [a.atFrame, b.atFrame], [0, 1], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      });
      cx = a.x + (b.x - a.x) * t;
      cy = a.y + (b.y - a.y) * t;
      break;
    }
    if (frame > b.atFrame) {
      cx = b.x;
      cy = b.y;
    }
  }

  // Click ripple — expanding circle that fades out
  const showRipple = clickAt !== undefined && frame >= clickAt && frame <= clickAt + 30;
  const rippleRadius = showRipple ? interpolate(frame, [clickAt, clickAt + 30], [8, 60]) : 0;
  const rippleOpacity = showRipple
    ? interpolate(frame, [clickAt, clickAt + 30], [0.7, 0])
    : 0;

  return (
    <>
      {showRipple && (
        <svg
          style={{ position: "absolute", inset: 0, pointerEvents: "none" }}
          width="100%"
          height="100%"
        >
          <circle
            cx={cx}
            cy={cy}
            r={rippleRadius}
            fill="none"
            stroke={PAI_THEME.colors.accent}
            strokeWidth={3}
            opacity={rippleOpacity}
          />
        </svg>
      )}
      {/* Cursor itself — simple pointer triangle */}
      <svg
        style={{
          position: "absolute",
          left: cx,
          top: cy,
          pointerEvents: "none",
          filter: "drop-shadow(0 2px 4px rgba(0,0,0,0.4))",
        }}
        width={32}
        height={32}
      >
        <path
          d="M 4 4 L 4 22 L 9 17 L 13 26 L 16 25 L 12 16 L 19 16 Z"
          fill={PAI_THEME.colors.text}
          stroke={PAI_THEME.colors.background}
          strokeWidth={1.5}
        />
      </svg>
    </>
  );
};
