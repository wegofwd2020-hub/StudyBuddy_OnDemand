import React, { useMemo } from "react";
import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { PAI_THEME } from "../theme";

/**
 * <ConfettiBurst> — subtle particle burst (~500ms total).
 *
 * Used scarcely — once per video at most. Story B slide 9 (streak
 * counter celebrating 12 nights). Particles emit from a centroid,
 * arc outward via linear motion + gravity, fade out after ~15 frames.
 *
 * @param at      Frame at which the burst should fire.
 * @param cx, cy  Origin of the burst (default centred).
 * @param count   Number of particles (default 24).
 */
export const ConfettiBurst: React.FC<{
  at: number;
  cx?: number;
  cy?: number;
  count?: number;
}> = ({ at, cx, cy, count = 24 }) => {
  const frame = useCurrentFrame();
  const { width, height } = useVideoConfig();
  const originX = cx ?? width / 2;
  const originY = cy ?? height / 2;

  // Stable per-particle params via memo (deterministic given count)
  const particles = useMemo(() => {
    return Array.from({ length: count }).map((_, i) => {
      const angle = (i / count) * Math.PI * 2 + (i * 0.37);
      const speed = 220 + (i % 5) * 40;
      const colors = [
        PAI_THEME.colors.accent,
        PAI_THEME.colors.accentLight,
        PAI_THEME.colors.success,
        PAI_THEME.colors.warning,
        PAI_THEME.colors.info,
      ];
      return {
        angle,
        speed,
        color: colors[i % colors.length],
        size: 8 + (i % 3) * 4,
      };
    });
  }, [count]);

  const elapsed = frame - at;
  if (elapsed < 0 || elapsed > 18) return null;

  const t = elapsed / 18; // 0 → 1
  const opacity = interpolate(elapsed, [0, 6, 18], [0, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <svg
      style={{ position: "absolute", inset: 0, pointerEvents: "none" }}
      width={width}
      height={height}
    >
      {particles.map((p, i) => {
        // Linear outward + gravity (y accelerates downward)
        const dx = Math.cos(p.angle) * p.speed * t;
        const dy = Math.sin(p.angle) * p.speed * t + 0.5 * 600 * t * t;
        return (
          <rect
            key={i}
            x={originX + dx - p.size / 2}
            y={originY + dy - p.size / 2}
            width={p.size}
            height={p.size}
            fill={p.color}
            opacity={opacity}
            transform={`rotate(${i * 22 + elapsed * 12} ${originX + dx} ${originY + dy})`}
          />
        );
      })}
    </svg>
  );
};
