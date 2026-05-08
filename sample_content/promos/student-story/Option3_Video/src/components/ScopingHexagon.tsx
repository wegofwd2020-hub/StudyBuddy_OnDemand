import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { PAI_THEME } from "../theme";

/**
 * <ScopingHexagon> — the centerpiece visual for Story A slide 3.
 *
 * Six labels orbit toward a glowing centroid and lock together as a
 * hexagonal arrangement. Each label springs in sequentially. After all
 * six lock, a connecting hexagon outline fades in at the centroid.
 *
 * The narration calls out each dimension by name; the per-dimension
 * appearance times below are tuned to land just before the
 * corresponding word.
 */
const DIMENSIONS = [
  { label: "Topic", color: PAI_THEME.colors.dim1, appearAt: 30 },
  { label: "Grade", color: PAI_THEME.colors.dim2, appearAt: 60 },
  { label: "Language", color: PAI_THEME.colors.dim3, appearAt: 90 },
  { label: "Curriculum context", color: PAI_THEME.colors.dim4, appearAt: 120 },
  { label: "Format", color: PAI_THEME.colors.dim5, appearAt: 150 },
  { label: "Real-world framing", color: PAI_THEME.colors.dim6, appearAt: 180 },
];

const RADIUS = 320;
const HEXAGON_LOCK_FRAME = 230;

export const ScopingHexagon: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const cx = width / 2;
  const cy = height / 2;

  const hexagonOpacity = interpolate(
    frame,
    [HEXAGON_LOCK_FRAME, HEXAGON_LOCK_FRAME + 30],
    [0, 1],
    { extrapolateRight: "clamp" },
  );

  // Compute the six anchor positions — six points around a circle
  const anchors = DIMENSIONS.map((d, i) => {
    // -90° offset puts the first label at the top
    const angle = -Math.PI / 2 + (i * 2 * Math.PI) / 6;
    return {
      ...d,
      anchorX: cx + RADIUS * Math.cos(angle),
      anchorY: cy + RADIUS * Math.sin(angle),
    };
  });

  return (
    <>
      {/* Connecting hexagon outline — fades in after all six dimensions lock */}
      <svg
        width={width}
        height={height}
        style={{ position: "absolute", inset: 0, opacity: hexagonOpacity }}
      >
        <polygon
          points={anchors.map((a) => `${a.anchorX},${a.anchorY}`).join(" ")}
          fill="none"
          stroke={PAI_THEME.colors.accentLight}
          strokeWidth={3}
          strokeDasharray="6 6"
        />
        {/* Lines from each anchor to the centroid */}
        {anchors.map((a, i) => (
          <line
            key={i}
            x1={a.anchorX}
            y1={a.anchorY}
            x2={cx}
            y2={cy}
            stroke={a.color}
            strokeWidth={2}
            opacity={0.45}
          />
        ))}
        {/* Centroid glow */}
        <circle
          cx={cx}
          cy={cy}
          r={45}
          fill={PAI_THEME.colors.accent}
          opacity={0.9}
        />
        <circle
          cx={cx}
          cy={cy}
          r={70}
          fill={PAI_THEME.colors.accent}
          opacity={0.25}
        />
      </svg>

      {/* Six dimension labels — each orbits in via spring */}
      {anchors.map((a, i) => {
        // Spring drives the label from off-canvas to its anchor position
        const t = spring({
          frame: frame - a.appearAt,
          fps,
          config: PAI_THEME.animation.springDefault,
          durationInFrames: 30,
        });
        // Start position: out beyond the hexagon
        const startMultiplier = 2.4;
        const startX = cx + RADIUS * startMultiplier * Math.cos(
          -Math.PI / 2 + (i * 2 * Math.PI) / 6,
        );
        const startY = cy + RADIUS * startMultiplier * Math.sin(
          -Math.PI / 2 + (i * 2 * Math.PI) / 6,
        );
        const x = interpolate(t, [0, 1], [startX, a.anchorX]);
        const y = interpolate(t, [0, 1], [startY, a.anchorY]);
        const opacity = interpolate(t, [0, 0.5, 1], [0, 1, 1]);

        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: x,
              top: y,
              transform: "translate(-50%, -50%)",
              opacity,
              backgroundColor: a.color,
              color: "#0f172a",
              fontSize: 28,
              fontWeight: 700,
              padding: "12px 24px",
              borderRadius: 999,
              boxShadow: `0 8px 24px ${a.color}55`,
              fontFamily: PAI_THEME.typography.fontFamily,
              whiteSpace: "nowrap",
            }}
          >
            {a.label}
          </div>
        );
      })}
    </>
  );
};
