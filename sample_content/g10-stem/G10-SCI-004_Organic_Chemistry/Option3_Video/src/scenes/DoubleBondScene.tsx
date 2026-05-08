/**
 * DoubleBondScene — alkene C=C double bond.
 *
 * Visualises the σ + π architecture of the double bond:
 *   - σ bond: in-line (the central axis line)
 *   - π bond: electron lobes ABOVE and BELOW the plane (the second
 *     overlap that makes the bond "double" and locks rotation)
 *
 * Then demonstrates locked rotation by attempting to rotate one CH₂
 * substituent and showing it doesn't move (red shake), and finally
 * shows cis/trans isomerism with 2-butene.
 *
 * Frames @ 30fps (24s = 720 frames):
 *   0–60     title fades in
 *   60–180   ethene appears (2 carbons + 4 hydrogens), σ bond highlighted
 *   180–330  π bond appears as electron clouds above + below
 *   330–480  rotation-attempt: try-and-fail shake + red lock badge
 *   480–660  cis ↔ trans 2-butene flip (substituents swap)
 *   660–720  caption fade-in
 */
import React from "react";
import { AbsoluteFill, useCurrentFrame, interpolate, spring, useVideoConfig } from "remotion";
import { PAI_THEME, doubleBondLines } from "../theme";

const STAGE_W = 1920;
const STAGE_H = 1080;
const CENTER_X = STAGE_W / 2;
const CENTER_Y = 560;

// 2-butene cis/trans state — stage 5
function ButeneFrame(props: { isTrans: boolean; opacity: number }) {
  const { isTrans, opacity } = props;
  const cLeft = CENTER_X - 110;
  const cRight = CENTER_X + 110;
  // CH₃ groups: cis = both top, trans = top + bottom
  const ch3LeftY = CENTER_Y - 110;
  const ch3RightY = isTrans ? CENTER_Y + 110 : CENTER_Y - 110;
  // H atoms (the other substituent on each carbon — opposite side)
  const hLeftY = CENTER_Y + 110;
  const hRightY = isTrans ? CENTER_Y - 110 : CENTER_Y + 110;
  return (
    <g opacity={opacity}>
      {/* C=C double bond */}
      {doubleBondLines(cLeft, CENTER_Y, cRight, CENTER_Y)}
      {/* Left carbon's substituents */}
      <line x1={cLeft} y1={CENTER_Y} x2={cLeft - 10} y2={ch3LeftY} stroke={PAI_THEME.colors.bondInkOnDark} strokeWidth={4} />
      <line x1={cLeft} y1={CENTER_Y} x2={cLeft - 10} y2={hLeftY} stroke={PAI_THEME.colors.bondInkOnDark} strokeWidth={4} />
      {/* Right carbon's substituents */}
      <line x1={cRight} y1={CENTER_Y} x2={cRight + 10} y2={ch3RightY} stroke={PAI_THEME.colors.bondInkOnDark} strokeWidth={4} />
      <line x1={cRight} y1={CENTER_Y} x2={cRight + 10} y2={hRightY} stroke={PAI_THEME.colors.bondInkOnDark} strokeWidth={4} />
      {/* Atoms */}
      <circle cx={cLeft} cy={CENTER_Y} r={28} fill={PAI_THEME.colors.carbon} stroke={PAI_THEME.colors.text} strokeWidth={2} />
      <text x={cLeft} y={CENTER_Y + 9} fontSize={28} fill={PAI_THEME.colors.text} textAnchor="middle" fontWeight={800}>C</text>
      <circle cx={cRight} cy={CENTER_Y} r={28} fill={PAI_THEME.colors.carbon} stroke={PAI_THEME.colors.text} strokeWidth={2} />
      <text x={cRight} y={CENTER_Y + 9} fontSize={28} fill={PAI_THEME.colors.text} textAnchor="middle" fontWeight={800}>C</text>
      {/* CH3 labels */}
      <text x={cLeft - 30} y={ch3LeftY + 8} fontSize={24} fill={PAI_THEME.colors.text} textAnchor="end" fontWeight={700}>CH₃</text>
      <text x={cRight + 30} y={ch3RightY + 8} fontSize={24} fill={PAI_THEME.colors.text} textAnchor="start" fontWeight={700}>CH₃</text>
      {/* H labels */}
      <text x={cLeft - 30} y={hLeftY + 8} fontSize={24} fill={PAI_THEME.colors.textMuted} textAnchor="end" fontWeight={700}>H</text>
      <text x={cRight + 30} y={hRightY + 8} fontSize={24} fill={PAI_THEME.colors.textMuted} textAnchor="start" fontWeight={700}>H</text>
    </g>
  );
}

export const DoubleBondScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const titleSpring = spring({ frame, fps, config: PAI_THEME.animation.springDefault });
  const titleOp = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: "clamp" });

  // Phase 2 (60-180): ethene appears
  const etheneOp = interpolate(frame, [60, 150], [0, 1], { extrapolateRight: "clamp" });
  // Phase 3 (180-330): π bond clouds appear above + below
  const piOp = interpolate(frame, [180, 280], [0, 1], { extrapolateRight: "clamp" });
  // Phase 4 (330-480): rotation-attempt shake
  const isShake = frame >= 330 && frame < 460;
  const shakeAmp = isShake ? 8 * Math.sin((frame - 330) * 0.6) : 0;
  const lockBadgeOp = interpolate(frame, [380, 440], [0, 1], { extrapolateRight: "clamp" });
  // Hide the shake/lock display from frame 480 onward (transition into cis/trans demo)
  const lockVisible = frame < 480;

  // Phase 5 (480-660): cis/trans 2-butene
  const butenePhaseOp = interpolate(frame, [490, 560], [0, 1], { extrapolateRight: "clamp" });
  // Toggle between cis and trans every 80 frames
  const isTrans = Math.floor((frame - 490) / 80) % 2 === 1;

  const captionOp = interpolate(frame, [660, 700], [0, 1], { extrapolateRight: "clamp" });

  // Carbon positions for the basic ethene visualisation (phases 2–4)
  const cLeft = CENTER_X - 90;
  const cRight = CENTER_X + 90;
  const hOffsetY = 70;

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
          2 of 4 — double bond
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
          C=C  (alkene)
        </h1>
      </div>

      {/* Ethene + lock display (phases 2–4) */}
      {lockVisible && (
        <svg width={STAGE_W} height={STAGE_H} style={{ position: "absolute", inset: 0 }}>
          {/* π electron clouds — render BEHIND the bonds */}
          <g opacity={piOp}>
            {/* upper lobe */}
            <ellipse
              cx={CENTER_X}
              cy={CENTER_Y - 28}
              rx={120}
              ry={26}
              fill={PAI_THEME.colors.pi}
              opacity={0.30}
            />
            {/* lower lobe */}
            <ellipse
              cx={CENTER_X}
              cy={CENTER_Y + 28}
              rx={120}
              ry={26}
              fill={PAI_THEME.colors.pi}
              opacity={0.30}
            />
          </g>

          {/* Ethene structure — wrap shake transform */}
          <g transform={`translate(${shakeAmp} 0)`} opacity={etheneOp}>
            {doubleBondLines(cLeft, CENTER_Y, cRight, CENTER_Y)}
            {/* H atoms on left carbon */}
            <line x1={cLeft} y1={CENTER_Y} x2={cLeft - 8} y2={CENTER_Y - hOffsetY} stroke={PAI_THEME.colors.bondInkOnDark} strokeWidth={3} />
            <line x1={cLeft} y1={CENTER_Y} x2={cLeft - 8} y2={CENTER_Y + hOffsetY} stroke={PAI_THEME.colors.bondInkOnDark} strokeWidth={3} />
            {/* H atoms on right carbon */}
            <line x1={cRight} y1={CENTER_Y} x2={cRight + 8} y2={CENTER_Y - hOffsetY} stroke={PAI_THEME.colors.bondInkOnDark} strokeWidth={3} />
            <line x1={cRight} y1={CENTER_Y} x2={cRight + 8} y2={CENTER_Y + hOffsetY} stroke={PAI_THEME.colors.bondInkOnDark} strokeWidth={3} />
            {/* Carbons */}
            <circle cx={cLeft} cy={CENTER_Y} r={32} fill={PAI_THEME.colors.carbon} stroke={PAI_THEME.colors.text} strokeWidth={2} />
            <text x={cLeft} y={CENTER_Y + 11} fontSize={32} fill={PAI_THEME.colors.text} textAnchor="middle" fontWeight={800}>C</text>
            <circle cx={cRight} cy={CENTER_Y} r={32} fill={PAI_THEME.colors.carbon} stroke={PAI_THEME.colors.text} strokeWidth={2} />
            <text x={cRight} y={CENTER_Y + 11} fontSize={32} fill={PAI_THEME.colors.text} textAnchor="middle" fontWeight={800}>C</text>
            {/* H labels */}
            <text x={cLeft - 14} y={CENTER_Y - hOffsetY + 5} fontSize={22} fill={PAI_THEME.colors.textMuted} textAnchor="end" fontWeight={700}>H</text>
            <text x={cLeft - 14} y={CENTER_Y + hOffsetY + 5} fontSize={22} fill={PAI_THEME.colors.textMuted} textAnchor="end" fontWeight={700}>H</text>
            <text x={cRight + 14} y={CENTER_Y - hOffsetY + 5} fontSize={22} fill={PAI_THEME.colors.textMuted} textAnchor="start" fontWeight={700}>H</text>
            <text x={cRight + 14} y={CENTER_Y + hOffsetY + 5} fontSize={22} fill={PAI_THEME.colors.textMuted} textAnchor="start" fontWeight={700}>H</text>
          </g>

          {/* π / σ labels (when π is shown) */}
          <g opacity={piOp}>
            <text
              x={CENTER_X}
              y={CENTER_Y - 90}
              fontSize={28}
              fill={PAI_THEME.colors.pi}
              textAnchor="middle"
              fontWeight={700}
              fontFamily={PAI_THEME.typography.fontFamily}
            >
              π bond
            </text>
            <text
              x={CENTER_X}
              y={CENTER_Y + 110}
              fontSize={28}
              fill={PAI_THEME.colors.pi}
              textAnchor="middle"
              fontWeight={700}
              fontFamily={PAI_THEME.typography.fontFamily}
            >
              π bond
            </text>
            <text
              x={CENTER_X}
              y={CENTER_Y - 50}
              fontSize={20}
              fill={PAI_THEME.colors.sigma}
              textAnchor="middle"
              fontWeight={700}
            >
              σ ↓
            </text>
          </g>

          {/* Lock badge */}
          {lockBadgeOp > 0 && (
            <g opacity={lockBadgeOp}>
              <rect
                x={CENTER_X - 200}
                y={CENTER_Y + 180}
                width={400}
                height={60}
                rx={30}
                fill={PAI_THEME.colors.error}
                opacity={0.92}
              />
              <text
                x={CENTER_X}
                y={CENTER_Y + 218}
                fontSize={24}
                fill={PAI_THEME.colors.text}
                textAnchor="middle"
                fontWeight={700}
                fontFamily={PAI_THEME.typography.fontFamily}
              >
                🔒 rotation locked by π bond
              </text>
            </g>
          )}
        </svg>
      )}

      {/* cis/trans 2-butene panel (phase 5) */}
      {!lockVisible && (
        <>
          <svg width={STAGE_W} height={STAGE_H} style={{ position: "absolute", inset: 0 }}>
            <ButeneFrame isTrans={isTrans} opacity={butenePhaseOp} />
          </svg>
          <div
            style={{
              position: "absolute",
              top: 280,
              left: 0,
              right: 0,
              textAlign: "center",
              opacity: butenePhaseOp,
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
              }}
            >
              2-butene  ·  cis ↔ trans
            </p>
            <h2
              style={{
                margin: "8px 0 0 0",
                color: PAI_THEME.colors.text,
                fontSize: 56,
                fontWeight: 700,
              }}
            >
              {isTrans ? "trans-2-butene" : "cis-2-butene"}
            </h2>
            <p
              style={{
                margin: "8px 0 0 0",
                color: PAI_THEME.colors.textMuted,
                fontSize: 22,
              }}
            >
              same atoms, different geometry — only possible because the C=C cannot rotate
            </p>
          </div>
        </>
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
          Alkenes — σ + π. sp² planar geometry. Rotation locked by the π overlap → cis/trans isomers exist.
        </p>
      </div>
    </AbsoluteFill>
  );
};
