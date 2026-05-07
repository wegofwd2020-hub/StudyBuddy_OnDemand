/**
 * MotionAlongStripScene — two stacked strips showing concurrent uniform vs
 * accelerated motion, with stroboscope dots accumulating every second.
 *
 * Physics (both end at the same point so the spacing pattern is the only
 * pedagogical signal):
 *
 *   Uniform:      x(t) = 5 t              v = 5 m/s,  x(6) = 30 m
 *   Accelerated:  x(t) = (5/6) t²         a = 5/3 m/s², x(6) = 30 m
 *
 * Strobe-dot spacing pattern at integer t = 1..6:
 *   Uniform:      5  10  15  20  25  30   (gaps: 5,  5,  5,  5,  5,  5)
 *   Accelerated:  0.83 3.33 7.5 13.3 20.8 30  (gaps: 0.83, 2.5, 4.17, 5.83, 7.5, 9.17)
 *
 * The accelerated row's gaps grow in the Galilean odd-number ratio 1:3:5:7:9:11.
 *
 * Frames @ 30fps (24 s total = 720 frames):
 *   0–60     title + subtitle fade in
 *   60–150   sub-heading and labels appear
 *   150–330  motion plays (t = 0 to t = 6 s)
 *   330–450  caption: "Strobe dots show position every second"
 *   450–570  callout: "Equal gaps → constant speed" (top strip)
 *   570–720  callout: "Growing gaps → speeding up" (bottom strip) + final tableau
 */
import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate, useVideoConfig, spring } from 'remotion';
import { PAI_THEME } from '../theme';

// ── Strip geometry ───────────────────────────────────────────────────────────
const STRIP_X0 = 200;
const STRIP_X1 = 1700;
const PX_PER_M = (STRIP_X1 - STRIP_X0) / 30; // 30 m visible
const Y_UNIFORM = 380;
const Y_ACCEL = 760;
const STROBE_OFFSET = 70;
const BALL_R = 22;
const STROBE_DOT_R = 10;

// ── Physics ─────────────────────────────────────────────────────────────────
const T_MAX = 6;
const xUniform = (t: number) => 5 * t;          // metres
const xAccel = (t: number) => (5 / 6) * t * t;  // metres

// Frame anchors
const F_TITLE_END = 60;
const F_SUBHEAD_END = 150;
const F_MOTION_START = 150;
const F_MOTION_END = 330; // 150 + 6s * 30fps
const F_CAP1_START = 330;
const F_CAP2_START = 450;
const F_CAP3_START = 570;

const tickPxUniform = (t: number) => STRIP_X0 + xUniform(t) * PX_PER_M;
const tickPxAccel = (t: number) => STRIP_X0 + xAccel(t) * PX_PER_M;

interface StripProps {
  y: number;
  color: string;
  ballPositionPx: number;
  visibleStrobeCount: number;       // how many integer-t dots to show
  strobePositions: number[];        // px positions of all 6 strobe dots
  label: string;
  labelColor: string;
  showSpacingMarkers: boolean;
  spacingMarkerColor: string;
}

const Strip: React.FC<StripProps> = ({
  y,
  color,
  ballPositionPx,
  visibleStrobeCount,
  strobePositions,
  label,
  labelColor,
  showSpacingMarkers,
  spacingMarkerColor,
}) => {
  return (
    <g>
      {/* Strip baseline */}
      <line
        x1={STRIP_X0 - 30} y1={y} x2={STRIP_X1 + 30} y2={y}
        stroke={PAI_THEME.colors.textMuted} strokeWidth={2.5} />
      {/* Right-end arrowhead */}
      <polygon
        points={`${STRIP_X1 + 30},${y} ${STRIP_X1 + 14},${y - 8} ${STRIP_X1 + 14},${y + 8}`}
        fill={PAI_THEME.colors.textMuted} />
      {/* Origin marker */}
      <line x1={STRIP_X0} y1={y - 14} x2={STRIP_X0} y2={y + 14}
        stroke={PAI_THEME.colors.textMuted} strokeWidth={2} />
      <text x={STRIP_X0} y={y + 36} fill={PAI_THEME.colors.textMuted}
        fontSize={20} textAnchor="middle">x = 0</text>
      <text x={STRIP_X1} y={y + 36} fill={PAI_THEME.colors.textMuted}
        fontSize={20} textAnchor="middle">x = 30 m</text>

      {/* Strobe dots (already-passed integer seconds) */}
      {strobePositions.slice(0, visibleStrobeCount).map((px, i) => (
        <g key={i}>
          <circle cx={px} cy={y + STROBE_OFFSET} r={STROBE_DOT_R}
            fill={color} stroke={PAI_THEME.colors.text} strokeWidth={1.5} opacity={0.9} />
          <text x={px} y={y + STROBE_OFFSET + 32} fill={PAI_THEME.colors.textMuted}
            fontSize={18} textAnchor="middle">t={i + 1}</text>
        </g>
      ))}

      {/* Spacing markers (only after motion ends) */}
      {showSpacingMarkers && strobePositions.slice(0, -1).map((px, i) => {
        const next = strobePositions[i + 1];
        if (next == null) return null;
        const yMark = y + STROBE_OFFSET + 60;
        return (
          <g key={`gap-${i}`}>
            <line x1={px + STROBE_DOT_R} y1={yMark} x2={next - STROBE_DOT_R} y2={yMark}
              stroke={spacingMarkerColor} strokeWidth={2} />
            <line x1={px + STROBE_DOT_R} y1={yMark - 6} x2={px + STROBE_DOT_R} y2={yMark + 6}
              stroke={spacingMarkerColor} strokeWidth={2} />
            <line x1={next - STROBE_DOT_R} y1={yMark - 6} x2={next - STROBE_DOT_R} y2={yMark + 6}
              stroke={spacingMarkerColor} strokeWidth={2} />
          </g>
        );
      })}

      {/* Moving ball */}
      <circle cx={ballPositionPx} cy={y} r={BALL_R}
        fill={color} stroke={PAI_THEME.colors.text} strokeWidth={3} />

      {/* Right-side label */}
      <text x={STRIP_X1 + 80} y={y + 8} fill={labelColor}
        fontSize={26} fontWeight={700}>{label}</text>
    </g>
  );
};

export const MotionAlongStripScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // ── Title timing ────────────────────────────────────────────────────────
  const titleScale = spring({ frame, fps, config: PAI_THEME.animation.springDefault });
  const titleOp = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: 'clamp' });
  const subOp = interpolate(frame, [20, 60], [0, 1], { extrapolateRight: 'clamp' });
  const subHeadOp = interpolate(frame, [60, F_SUBHEAD_END], [0, 1], { extrapolateRight: 'clamp' });

  // ── Physics-time ────────────────────────────────────────────────────────
  const motionFrame = Math.max(0, Math.min(frame - F_MOTION_START, F_MOTION_END - F_MOTION_START));
  const t = motionFrame / fps;

  const ballUniformPx = STRIP_X0 + xUniform(t) * PX_PER_M;
  const ballAccelPx = STRIP_X0 + xAccel(t) * PX_PER_M;

  // Strobe dot positions (precomputed for all 6 integer seconds)
  const strobeUniform = [1, 2, 3, 4, 5, 6].map(tickPxUniform);
  const strobeAccel = [1, 2, 3, 4, 5, 6].map(tickPxAccel);

  // Visible-dot count grows with t
  const visibleStrobes = Math.floor(t);

  // Spacing markers appear once motion completes
  const showSpacingMarkers = frame >= F_MOTION_END;

  // ── Caption fades ───────────────────────────────────────────────────────
  const cap1Op = interpolate(frame, [F_CAP1_START, F_CAP1_START + 40], [0, 1], { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' });
  const cap2Op = interpolate(frame, [F_CAP2_START, F_CAP2_START + 40], [0, 1], { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' });
  const cap3Op = interpolate(frame, [F_CAP3_START, F_CAP3_START + 40], [0, 1], { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' });

  return (
    <AbsoluteFill style={{
      background: `linear-gradient(135deg, ${PAI_THEME.colors.background}, ${PAI_THEME.colors.backgroundAlt})`,
      fontFamily: PAI_THEME.typography.fontFamily,
    }}>
      {/* Title */}
      <div style={{
        position: 'absolute', top: 30, left: 0, right: 0,
        textAlign: 'center',
      }}>
        <h1 style={{
          fontSize: 56, color: PAI_THEME.colors.text, margin: 0,
          opacity: titleOp, transform: `scale(${titleScale})`,
        }}>
          Motion Along a Strip — Uniform vs Accelerated
        </h1>
        <p style={{
          fontSize: 26, color: PAI_THEME.colors.accentLight, marginTop: 6, fontStyle: 'italic',
          opacity: subOp,
        }}>
          Same 6 seconds. Same finish line. Different stories.
        </p>
        <p style={{
          fontSize: 22, color: PAI_THEME.colors.textMuted, marginTop: 4,
          opacity: subHeadOp,
        }}>
          Watch the spacing of the strobe dots — it tells you everything.
        </p>
      </div>

      {/* Strips */}
      <svg width={1920} height={1080} viewBox="0 0 1920 1080"
        style={{ position: 'absolute', inset: 0 }}>
        <Strip
          y={Y_UNIFORM}
          color={PAI_THEME.colors.accent}
          ballPositionPx={ballUniformPx}
          visibleStrobeCount={visibleStrobes}
          strobePositions={strobeUniform}
          label="uniform · v = 5 m/s"
          labelColor={PAI_THEME.colors.accent}
          showSpacingMarkers={showSpacingMarkers}
          spacingMarkerColor={PAI_THEME.colors.success}
        />
        <Strip
          y={Y_ACCEL}
          color={PAI_THEME.colors.warning}
          ballPositionPx={ballAccelPx}
          visibleStrobeCount={visibleStrobes}
          strobePositions={strobeAccel}
          label="accelerated · a = 5/6 m/s²"
          labelColor={PAI_THEME.colors.warning}
          showSpacingMarkers={showSpacingMarkers}
          spacingMarkerColor={PAI_THEME.colors.error}
        />

        {/* Live time readout */}
        {frame >= F_MOTION_START && frame <= F_MOTION_END + 30 && (
          <g>
            <text x={1820} y={210} fill={PAI_THEME.colors.text}
              fontSize={28} fontWeight={700} textAnchor="end">
              t = {t.toFixed(1)} s
            </text>
          </g>
        )}
      </svg>

      {/* Captions (post-motion) */}
      <div style={{
        position: 'absolute', top: 950, left: 0, right: 0,
        textAlign: 'center',
        fontSize: 28, fontWeight: 700,
      }}>
        <div style={{
          color: PAI_THEME.colors.text,
          opacity: cap1Op, marginBottom: 6,
        }}>
          Strobe dots = the ball's position every second.
        </div>
        <div style={{
          color: PAI_THEME.colors.success,
          opacity: cap2Op, marginBottom: 6,
        }}>
          ▲ Equal gaps every second → constant speed (uniform)
        </div>
        <div style={{
          color: PAI_THEME.colors.error,
          opacity: cap3Op,
        }}>
          ▼ Gaps grow each second → speeding up (accelerated)
        </div>
      </div>
    </AbsoluteFill>
  );
};
