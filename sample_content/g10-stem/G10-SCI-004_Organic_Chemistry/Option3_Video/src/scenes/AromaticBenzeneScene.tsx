/**
 * AromaticBenzeneScene — benzene's delocalised aromatic system.
 *
 * Three-phase reveal:
 *   1. Hexagonal C₆ ring assembles vertex-by-vertex
 *   2. Alternating single/double bonds appear (Kekulé structure)
 *   3. Single + double bonds dissolve into a continuous π electron
 *      cloud — the delocalised aromatic system, with bond order 1.5
 *      everywhere
 *
 * Frames @ 30fps (24s = 720 frames):
 *   0–60     title fades in
 *   60–240   ring + 6 carbons assemble (one vertex every 30 frames)
 *   240–360  Kekulé alternating double-bond pattern fades in
 *   360–480  Kekulé "shimmer" — alternation flips back and forth to hint
 *            that neither single-form is the true picture
 *   480–600  alternating bonds dissolve; delocalised π cloud rings emerge
 *            (donut above + below the plane)
 *   600–720  caption fade-in (with the cloud held visible)
 */
import React from "react";
import { AbsoluteFill, useCurrentFrame, interpolate, spring, useVideoConfig } from "remotion";
import { PAI_THEME, doubleBondLines, singleBondLine } from "../theme";

const STAGE_W = 1920;
const STAGE_H = 1080;
const CENTER_X = STAGE_W / 2;
const CENTER_Y = 540;
const RING_R = 180; // hexagon circumradius

// Six vertex positions, starting top-right and going clockwise:
//   v0 = top-right, v1 = right, v2 = bottom-right,
//   v3 = bottom-left, v4 = left, v5 = top-left
function hexVertex(i: number): { x: number; y: number } {
  const angle = -Math.PI / 2 + (i * Math.PI) / 3; // 60° steps, starting at 12 o'clock
  return {
    x: CENTER_X + RING_R * Math.cos(angle),
    y: CENTER_Y + RING_R * Math.sin(angle),
  };
}

export const AromaticBenzeneScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const titleSpring = spring({ frame, fps, config: PAI_THEME.animation.springDefault });
  const titleOp = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: "clamp" });

  // Vertex appearance: each vertex appears at frame 60 + i*30
  const vertexOpacities = [0, 1, 2, 3, 4, 5].map((i) =>
    interpolate(frame, [60 + i * 24, 60 + i * 24 + 18], [0, 1], { extrapolateRight: "clamp" }),
  );
  // Each edge between i and (i+1)%6 appears once both vertices are in
  const edgeOpacities = [0, 1, 2, 3, 4, 5].map((i) => {
    const start = 60 + (i + 1) * 24;
    return interpolate(frame, [start, start + 14], [0, 1], { extrapolateRight: "clamp" });
  });

  // Phase 2 (240–360): Kekulé alternation appears.
  // We promote bonds at indices 0, 2, 4 to double — keeping the parity flip below in phase 3.
  const kekuleOp = interpolate(frame, [240, 320], [0, 1], { extrapolateRight: "clamp" });

  // Phase 3 (360–480): "shimmer" — the alternating pattern flips between
  // {0,2,4 double} and {1,3,5 double} every 30 frames to suggest neither
  // is the real picture.
  const shimmerActive = frame >= 360 && frame < 480;
  const altParity = shimmerActive ? Math.floor((frame - 360) / 30) % 2 : 0;

  // Phase 4 (480–600): the alternation dissolves and the delocalised
  // π electron cloud (a coloured ring) takes over.
  const kekuleFade = interpolate(frame, [480, 540], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const cloudOp = interpolate(frame, [480, 580], [0, 1], { extrapolateRight: "clamp" });

  // Caption
  const captionOp = interpolate(frame, [600, 660], [0, 1], { extrapolateRight: "clamp" });

  // Edge-double-or-single: in shimmer phase, parity flips. Double indices = altParity == 0 → {0,2,4}; altParity == 1 → {1,3,5}.
  const isDouble = (edgeIdx: number): boolean => {
    if (frame < 240) return false;
    if (frame >= 480) return false; // dissolved
    return shimmerActive
      ? edgeIdx % 2 === altParity
      : edgeIdx % 2 === 0;
  };

  return (
    <AbsoluteFill style={{ backgroundColor: PAI_THEME.colors.background }}>
      {/* Title */}
      <div
        style={{
          position: "absolute",
          top: 80,
          left: 0,
          right: 0,
          textAlign: "center",
          opacity: titleOp,
          transform: `scale(${interpolate(titleSpring, [0, 1], [0.92, 1])})`,
        }}
      >
        <p
          style={{
            margin: 0,
            color: PAI_THEME.colors.accentLight,
            fontSize: 30,
            fontWeight: 700,
            letterSpacing: 2,
            textTransform: "uppercase",
            fontFamily: PAI_THEME.typography.fontFamilyMono,
          }}
        >
          4 of 4 — aromatic
        </p>
        <h1
          style={{
            margin: "8px 0 0 0",
            color: PAI_THEME.colors.text,
            fontSize: 68,
            fontWeight: 800,
            letterSpacing: -1,
            fontFamily: PAI_THEME.typography.fontFamily,
          }}
        >
          benzene  (C₆H₆)
        </h1>
      </div>

      <svg width={STAGE_W} height={STAGE_H} style={{ position: "absolute", inset: 0 }}>
        {/* Delocalised π cloud — drawn behind everything */}
        <g opacity={cloudOp}>
          {/* outer halo */}
          <circle
            cx={CENTER_X}
            cy={CENTER_Y}
            r={RING_R + 60}
            fill="none"
            stroke={PAI_THEME.colors.delocalised}
            strokeWidth={36}
            opacity={0.18}
          />
          {/* inner halo */}
          <circle
            cx={CENTER_X}
            cy={CENTER_Y}
            r={RING_R - 20}
            fill="none"
            stroke={PAI_THEME.colors.delocalised}
            strokeWidth={26}
            opacity={0.30}
          />
          {/* core ring */}
          <circle
            cx={CENTER_X}
            cy={CENTER_Y}
            r={RING_R - 65}
            fill="none"
            stroke={PAI_THEME.colors.delocalised}
            strokeWidth={6}
            opacity={0.85}
          />
        </g>

        {/* Edges: 6 hexagon sides */}
        {[0, 1, 2, 3, 4, 5].map((i) => {
          const a = hexVertex(i);
          const b = hexVertex((i + 1) % 6);
          const edgeOp = edgeOpacities[i] * kekuleFade;
          if (edgeOp <= 0.01) return null;
          if (isDouble(i)) {
            return (
              <g key={`edge-${i}`} opacity={edgeOp * kekuleOp}>
                {doubleBondLines(a.x, a.y, b.x, b.y)}
              </g>
            );
          }
          return (
            <g key={`edge-${i}`} opacity={edgeOp}>
              {singleBondLine(a.x, a.y, b.x, b.y)}
            </g>
          );
        })}

        {/* Vertices: 6 carbon atoms */}
        {[0, 1, 2, 3, 4, 5].map((i) => {
          const v = hexVertex(i);
          return (
            <g key={`vertex-${i}`} opacity={vertexOpacities[i]}>
              <circle cx={v.x} cy={v.y} r={28} fill={PAI_THEME.colors.carbon} stroke={PAI_THEME.colors.text} strokeWidth={2} />
              <text x={v.x} y={v.y + 9} fontSize={26} fill={PAI_THEME.colors.text} textAnchor="middle" fontWeight={800}>
                C
              </text>
            </g>
          );
        })}
      </svg>

      {/* Stage labels */}
      {kekuleOp > 0 && kekuleFade > 0.5 && (
        <div
          style={{
            position: "absolute",
            top: CENTER_Y - RING_R - 90,
            left: 0,
            right: 0,
            textAlign: "center",
            opacity: kekuleOp * kekuleFade,
          }}
        >
          <p
            style={{
              margin: 0,
              color: PAI_THEME.colors.warning,
              fontSize: 24,
              fontWeight: 700,
              letterSpacing: 1.4,
              textTransform: "uppercase",
              fontFamily: PAI_THEME.typography.fontFamilyMono,
            }}
          >
            Kekulé — alternating single + double
          </p>
        </div>
      )}
      {cloudOp > 0 && (
        <div
          style={{
            position: "absolute",
            top: CENTER_Y - RING_R - 90,
            left: 0,
            right: 0,
            textAlign: "center",
            opacity: cloudOp,
          }}
        >
          <p
            style={{
              margin: 0,
              color: PAI_THEME.colors.delocalised,
              fontSize: 26,
              fontWeight: 700,
              letterSpacing: 1.4,
              textTransform: "uppercase",
              fontFamily: PAI_THEME.typography.fontFamilyMono,
            }}
          >
            delocalised — bond order 1.5 everywhere
          </p>
        </div>
      )}

      {/* Lower-third caption */}
      <div
        style={{
          position: "absolute",
          bottom: 80,
          left: "10%",
          right: "10%",
          padding: "16px 28px",
          backgroundColor: "rgba(15,23,42,0.85)",
          border: `1px solid ${PAI_THEME.colors.textDark}`,
          borderRadius: 10,
          opacity: captionOp,
        }}
      >
        <p
          style={{
            margin: 0,
            color: PAI_THEME.colors.text,
            fontSize: 26,
            lineHeight: 1.4,
            textAlign: "center",
            fontFamily: PAI_THEME.typography.fontFamily,
          }}
        >
          Aromatic — π electrons delocalise around the ring. All six C–C bonds are equivalent (1.5 bond order). Extra-stable.
        </p>
      </div>
    </AbsoluteFill>
  );
};
