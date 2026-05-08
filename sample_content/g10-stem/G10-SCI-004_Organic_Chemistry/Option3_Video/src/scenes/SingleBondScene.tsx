/**
 * SingleBondScene — alkane C–C single bond.
 *
 * Shows two methyl groups (CH₃) approaching each other and forming the
 * ethane molecule, with the shared electron pair revealed as a glowing
 * dot on the bond axis. Then the C–C axis spins to demonstrate the free
 * rotation that single bonds permit.
 *
 * Frames @ 30fps (24s = 720 frames):
 *   0–60     title fades in
 *   60–180   two CH₃ groups appear left + right, separated
 *   180–360  groups slide together; electron pair appears on the bond axis
 *   360–540  C–C axis spins ~3π demonstrating free rotation
 *   540–720  caption: "σ bond — single shared electron pair, free rotation"
 */
import React from "react";
import { AbsoluteFill, useCurrentFrame, interpolate, spring, useVideoConfig } from "remotion";
import { PAI_THEME, singleBondLine } from "../theme";

const STAGE_W = 1920;
const STAGE_H = 1080;
const CENTER_X = STAGE_W / 2;
const CENTER_Y = 540;

// Methyl-group rendering (CH₃) — one bonded carbon + three hydrogens
function MethylGroup(props: {
  cx: number;
  cy: number;
  rotation?: number; // degrees, around (cx, cy)
  showElectron?: boolean; // a single dot at one of the H positions
  flipForRight?: boolean; // mirror so the bond-side C points inward
}) {
  const { cx, cy, rotation = 0, showElectron = false, flipForRight = false } = props;
  const carbonR = 30;
  const hR = 14;
  const sign = flipForRight ? -1 : 1;
  const bondLen = 70;
  // Three H positions: bond-side gets nothing (it bonds to the other C);
  // place 3 H's on the OPPOSITE side spread at ±55° + straight back.
  const hOffsets = [
    { dx: -bondLen * sign, dy: 0 },
    { dx: -bondLen * 0.5 * sign, dy: -bondLen * 0.85 },
    { dx: -bondLen * 0.5 * sign, dy: bondLen * 0.85 },
  ];
  return (
    <g transform={`rotate(${rotation} ${cx} ${cy})`}>
      {hOffsets.map((h, i) => (
        <g key={i}>
          <line
            x1={cx}
            y1={cy}
            x2={cx + h.dx}
            y2={cy + h.dy}
            stroke={PAI_THEME.colors.bondInkOnDark}
            strokeWidth={3}
            strokeLinecap="round"
          />
          <circle cx={cx + h.dx} cy={cy + h.dy} r={hR} fill={PAI_THEME.colors.hydrogen} />
          <text
            x={cx + h.dx}
            y={cy + h.dy + 6}
            fontSize={18}
            fill={PAI_THEME.colors.background}
            textAnchor="middle"
            fontWeight={700}
          >
            H
          </text>
        </g>
      ))}
      <circle cx={cx} cy={cy} r={carbonR} fill={PAI_THEME.colors.carbon} stroke={PAI_THEME.colors.text} strokeWidth={2} />
      <text
        x={cx}
        y={cy + 9}
        fontSize={28}
        fill={PAI_THEME.colors.text}
        textAnchor="middle"
        fontWeight={800}
      >
        C
      </text>
      {showElectron && (
        <circle cx={cx + sign * 20} cy={cy} r={5} fill={PAI_THEME.colors.sigma} />
      )}
    </g>
  );
}

export const SingleBondScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const titleSpring = spring({ frame, fps, config: PAI_THEME.animation.springDefault });
  const titleOp = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: "clamp" });

  // Methyl group positions: start far apart, slide together by frame 360.
  // After frame 360, sit at final touching positions; rotation kicks in.
  const sep = interpolate(frame, [180, 360], [600, 250], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const leftCx = CENTER_X - sep / 2;
  const rightCx = CENTER_X + sep / 2;

  // Bond-axis rotation (rad). Free-rotation phase: frames 360–540.
  // Rotate ~540° (3π) so the demo reads.
  const bondRotationDeg = interpolate(frame, [360, 540], [0, 540], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Once the methyls touch, treat them as a rigid rotor: both rotate
  // around the midpoint of the bond. Apply the bond rotation only
  // *after* they have come together.
  const showAsRotor = frame >= 360;

  // Sigma electron pair: appears at frame 240 (during the slide-together)
  const sigmaOp = interpolate(frame, [240, 320], [0, 1], { extrapolateRight: "clamp" });
  const sigmaPulse = 1 + 0.15 * Math.sin((frame - 240) * 0.18);

  // Caption fade-in
  const captionOp = interpolate(frame, [540, 600], [0, 1], { extrapolateRight: "clamp" });

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
          1 of 4 — single bond
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
          C–C  (alkane)
        </h1>
      </div>

      <svg width={STAGE_W} height={STAGE_H} style={{ position: "absolute", inset: 0 }}>
        {showAsRotor ? (
          <g transform={`rotate(${bondRotationDeg} ${CENTER_X} ${CENTER_Y})`}>
            {/* C–C single bond (rendered first so it sits behind the C atoms) */}
            {singleBondLine(leftCx, CENTER_Y, rightCx, CENTER_Y)}
            <MethylGroup cx={leftCx} cy={CENTER_Y} flipForRight={false} />
            <MethylGroup cx={rightCx} cy={CENTER_Y} flipForRight={true} />
            {/* Sigma electron pair sits in the middle of the C–C bond */}
            <g opacity={sigmaOp}>
              <circle
                cx={CENTER_X}
                cy={CENTER_Y}
                r={14 * sigmaPulse}
                fill={PAI_THEME.colors.sigma}
                opacity={0.28}
              />
              <circle cx={CENTER_X - 6} cy={CENTER_Y} r={5} fill={PAI_THEME.colors.sigma} />
              <circle cx={CENTER_X + 6} cy={CENTER_Y} r={5} fill={PAI_THEME.colors.sigma} />
            </g>
          </g>
        ) : (
          <>
            {/* Pre-bond phase: two separate methyl groups + the bond emerging only after they're close */}
            {sep < 280 && singleBondLine(leftCx, CENTER_Y, rightCx, CENTER_Y)}
            <MethylGroup cx={leftCx} cy={CENTER_Y} flipForRight={false} />
            <MethylGroup cx={rightCx} cy={CENTER_Y} flipForRight={true} />
            {sep < 320 && (
              <g opacity={sigmaOp}>
                <circle
                  cx={CENTER_X}
                  cy={CENTER_Y}
                  r={14 * sigmaPulse}
                  fill={PAI_THEME.colors.sigma}
                  opacity={0.28}
                />
                <circle cx={CENTER_X - 6} cy={CENTER_Y} r={5} fill={PAI_THEME.colors.sigma} />
                <circle cx={CENTER_X + 6} cy={CENTER_Y} r={5} fill={PAI_THEME.colors.sigma} />
              </g>
            )}
          </>
        )}
      </svg>

      {/* Annotations */}
      {sigmaOp > 0 && (
        <div
          style={{
            position: "absolute",
            top: CENTER_Y + 90,
            left: 0,
            right: 0,
            textAlign: "center",
            opacity: sigmaOp,
          }}
        >
          <p
            style={{
              margin: 0,
              color: PAI_THEME.colors.sigma,
              fontSize: 28,
              fontWeight: 700,
              fontFamily: PAI_THEME.typography.fontFamily,
            }}
          >
            σ bond — one shared electron pair
          </p>
        </div>
      )}

      {showAsRotor && (
        <div
          style={{
            position: "absolute",
            bottom: 220,
            left: 0,
            right: 0,
            textAlign: "center",
            color: PAI_THEME.colors.warning,
            fontSize: 24,
            fontWeight: 700,
            fontFamily: PAI_THEME.typography.fontFamilyMono,
            letterSpacing: 1.4,
            textTransform: "uppercase",
          }}
        >
          ▸ axis rotates freely
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
          Alkanes — single C–C bonds (one σ bond). sp³ carbons. Free rotation around the bond axis.
        </p>
      </div>
    </AbsoluteFill>
  );
};
