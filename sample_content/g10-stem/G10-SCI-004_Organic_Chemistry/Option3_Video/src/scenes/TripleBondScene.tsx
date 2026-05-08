/**
 * TripleBondScene — alkyne C≡C triple bond.
 *
 * Builds up the bond layer-by-layer to show the σ + 2π architecture.
 * Then highlights the linear (180°) geometry with a measured arc, and
 * compares bond lengths against alkene + alkane to show the triple bond
 * is the shortest.
 *
 * Frames @ 30fps (24s = 720 frames):
 *   0–60     title fades in
 *   60–180   ethyne (H–C≡C–H) appears, σ bond first
 *   180–300  π bond #1 appears (vertical electron cloud)
 *   300–420  π bond #2 appears (horizontal — perpendicular to first)
 *   420–540  linear-geometry callout: 180° arc + "linear sp"
 *   540–660  bond-length comparison: alkane > alkene > alkyne
 *   660–720  caption fade-in
 */
import React from "react";
import { AbsoluteFill, useCurrentFrame, interpolate, spring, useVideoConfig } from "remotion";
import { PAI_THEME, tripleBondLines } from "../theme";

const STAGE_W = 1920;
const STAGE_H = 1080;
const CENTER_X = STAGE_W / 2;
const CENTER_Y = 480;

export const TripleBondScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const titleSpring = spring({ frame, fps, config: PAI_THEME.animation.springDefault });
  const titleOp = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: "clamp" });

  const etheneAppears = interpolate(frame, [60, 150], [0, 1], { extrapolateRight: "clamp" });
  // π bonds reveal sequentially
  const pi1Op = interpolate(frame, [180, 270], [0, 1], { extrapolateRight: "clamp" });
  const pi2Op = interpolate(frame, [300, 390], [0, 1], { extrapolateRight: "clamp" });

  // Linear-geometry callout fade
  const linearOp = interpolate(frame, [420, 480], [0, 1], { extrapolateRight: "clamp" });
  const linearFadeOut = interpolate(frame, [520, 540], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const linearVisible = linearOp * linearFadeOut;

  // Bond-length comparison
  const cmpOp = interpolate(frame, [540, 600], [0, 1], { extrapolateRight: "clamp" });

  const captionOp = interpolate(frame, [660, 700], [0, 1], { extrapolateRight: "clamp" });

  const cLeft = CENTER_X - 100;
  const cRight = CENTER_X + 100;

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
          3 of 4 — triple bond
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
          C≡C  (alkyne)
        </h1>
      </div>

      <svg width={STAGE_W} height={STAGE_H} style={{ position: "absolute", inset: 0 }}>
        {/* π bond #1 — vertical lobes (above + below) */}
        <g opacity={pi1Op}>
          <ellipse cx={CENTER_X} cy={CENTER_Y - 30} rx={130} ry={28} fill={PAI_THEME.colors.pi} opacity={0.35} />
          <ellipse cx={CENTER_X} cy={CENTER_Y + 30} rx={130} ry={28} fill={PAI_THEME.colors.pi} opacity={0.35} />
        </g>
        {/* π bond #2 — horizontal lobes (front + back, drawn as left + right of axis to read in 2D) */}
        <g opacity={pi2Op}>
          <ellipse
            cx={CENTER_X}
            cy={CENTER_Y}
            rx={150}
            ry={20}
            fill={PAI_THEME.colors.pi}
            opacity={0.22}
            transform={`rotate(0 ${CENTER_X} ${CENTER_Y})`}
          />
          <ellipse
            cx={CENTER_X}
            cy={CENTER_Y}
            rx={140}
            ry={50}
            fill={PAI_THEME.colors.pi}
            opacity={0.18}
          />
        </g>

        {/* Ethyne main structure */}
        <g opacity={etheneAppears}>
          {/* H — left of left C (linear axis) */}
          <line x1={cLeft - 80} y1={CENTER_Y} x2={cLeft - 32} y2={CENTER_Y} stroke={PAI_THEME.colors.bondInkOnDark} strokeWidth={4} strokeLinecap="round" />
          <text x={cLeft - 100} y={CENTER_Y + 9} fontSize={32} fill={PAI_THEME.colors.textMuted} textAnchor="end" fontWeight={700}>H</text>
          {/* C≡C triple bond */}
          {tripleBondLines(cLeft, CENTER_Y, cRight, CENTER_Y)}
          {/* Carbons */}
          <circle cx={cLeft} cy={CENTER_Y} r={32} fill={PAI_THEME.colors.carbon} stroke={PAI_THEME.colors.text} strokeWidth={2} />
          <text x={cLeft} y={CENTER_Y + 11} fontSize={32} fill={PAI_THEME.colors.text} textAnchor="middle" fontWeight={800}>C</text>
          <circle cx={cRight} cy={CENTER_Y} r={32} fill={PAI_THEME.colors.carbon} stroke={PAI_THEME.colors.text} strokeWidth={2} />
          <text x={cRight} y={CENTER_Y + 11} fontSize={32} fill={PAI_THEME.colors.text} textAnchor="middle" fontWeight={800}>C</text>
          {/* H — right of right C */}
          <line x1={cRight + 32} y1={CENTER_Y} x2={cRight + 80} y2={CENTER_Y} stroke={PAI_THEME.colors.bondInkOnDark} strokeWidth={4} strokeLinecap="round" />
          <text x={cRight + 100} y={CENTER_Y + 9} fontSize={32} fill={PAI_THEME.colors.textMuted} textAnchor="start" fontWeight={700}>H</text>
        </g>

        {/* π labels */}
        {pi1Op > 0 && (
          <text x={CENTER_X} y={CENTER_Y - 90} fontSize={26} fill={PAI_THEME.colors.pi} textAnchor="middle" fontWeight={700} fontFamily={PAI_THEME.typography.fontFamily} opacity={pi1Op}>
            π bond #1
          </text>
        )}
        {pi2Op > 0 && (
          <text x={CENTER_X + 220} y={CENTER_Y + 8} fontSize={26} fill={PAI_THEME.colors.pi} textAnchor="start" fontWeight={700} fontFamily={PAI_THEME.typography.fontFamily} opacity={pi2Op}>
            π bond #2
          </text>
        )}
      </svg>

      {/* Linear-geometry callout — appears after π2 reveals */}
      {linearVisible > 0 && (
        <div
          style={{
            position: "absolute",
            top: CENTER_Y + 80,
            left: 0,
            right: 0,
            textAlign: "center",
            opacity: linearVisible,
          }}
        >
          <p
            style={{
              margin: 0,
              color: PAI_THEME.colors.success,
              fontSize: 28,
              fontWeight: 700,
              fontFamily: PAI_THEME.typography.fontFamily,
            }}
          >
            ▸ 180° — linear geometry, sp hybridised
          </p>
        </div>
      )}

      {/* Bond-length comparison */}
      {cmpOp > 0 && (
        <div
          style={{
            position: "absolute",
            bottom: 200,
            left: "10%",
            right: "10%",
            opacity: cmpOp,
            fontFamily: PAI_THEME.typography.fontFamily,
          }}
        >
          <p
            style={{
              margin: 0,
              color: PAI_THEME.colors.warning,
              fontSize: 22,
              fontWeight: 700,
              letterSpacing: 1.5,
              textTransform: "uppercase",
              textAlign: "center",
            }}
          >
            bond length comparison (Å)
          </p>
          <div style={{ display: "flex", gap: 28, justifyContent: "center", marginTop: 16 }}>
            {[
              { label: "C–C alkane", length: 1.54, barLen: 280 },
              { label: "C=C alkene", length: 1.34, barLen: 244 },
              { label: "C≡C alkyne", length: 1.20, barLen: 218 },
            ].map((row, i) => (
              <div
                key={i}
                style={{
                  flex: 1,
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  gap: 8,
                  padding: 16,
                  backgroundColor: PAI_THEME.colors.backgroundAlt,
                  borderRadius: 10,
                  border: `2px solid ${
                    i === 2 ? PAI_THEME.colors.success : PAI_THEME.colors.textDark
                  }`,
                }}
              >
                <div
                  style={{
                    height: 12,
                    width: row.barLen,
                    backgroundColor: i === 2 ? PAI_THEME.colors.success : PAI_THEME.colors.accentLight,
                    borderRadius: 6,
                  }}
                />
                <p style={{ margin: 0, color: PAI_THEME.colors.text, fontSize: 22, fontWeight: 700 }}>
                  {row.label}
                </p>
                <p style={{ margin: 0, color: PAI_THEME.colors.textMuted, fontSize: 18 }}>
                  {row.length.toFixed(2)} Å
                </p>
              </div>
            ))}
          </div>
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
          Alkynes — σ + 2π. sp linear (180°). Shortest C–C bond. Acetylene (ethyne) is the simplest example.
        </p>
      </div>
    </AbsoluteFill>
  );
};
