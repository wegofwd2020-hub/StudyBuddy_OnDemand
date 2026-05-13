import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate, spring, useVideoConfig } from 'remotion';
import { PAI_THEME } from '../theme';

/**
 * Animated secant-to-tangent on  y = x²  with fixed point P = (1, 1).
 *
 * Q slides down the curve from x = 3 toward x = 1.  The secant line through
 * P and Q rotates accordingly.  Slope of secant PQ is exactly  q + 1
 * (since (q² − 1)/(q − 1) = q + 1), so as q → 1 the slope → 2 = f'(1).
 *
 * Stage layout (5 stages × 150 frames + 60-frame outro = 810 frames ≈ 27 s):
 *   stage 0 (q = 3.0,  m = 4.0)
 *   stage 1 (q = 2.0,  m = 3.0)
 *   stage 2 (q = 1.5,  m = 2.5)
 *   stage 3 (q = 1.2,  m = 2.2)
 *   stage 4 (q = 1.05, m = 2.05  ≈ tangent slope 2)
 *   outro: tangent line locks in at slope 2; reveal derivative formula.
 */

const STAGE_FRAMES = 150;
const NUM_STAGES = 5;
const OUTRO_FRAMES = 60;
// 5 × 150 + 60 = 810 frames (kept in sync with Root.tsx).

const Q_VALUES = [3.0, 2.0, 1.5, 1.2, 1.05]; // values of Q's x-coordinate at the END of each stage

// Slopes (for display) — exactly q + 1 by the algebra of the difference quotient on y = x²
const slopeAt = (q: number) => q + 1;

// Plot bounds (math coordinates)
const X_MIN = -0.5;
const X_MAX = 3.6;
const Y_MIN = -1.0;
const Y_MAX = 9.5;

// Plot pixel rect (inside the SVG) — the SVG itself is 1280 × 760 to leave room for chrome
const PLOT_W = 1280;
const PLOT_H = 760;

const xToPx = (x: number) => ((x - X_MIN) / (X_MAX - X_MIN)) * PLOT_W;
const yToPx = (y: number) => PLOT_H - ((y - Y_MIN) / (Y_MAX - Y_MIN)) * PLOT_H;

// y = x² parabola path
const buildParabolaPath = () => {
  const pts: string[] = [];
  const N = 240;
  for (let i = 0; i <= N; i++) {
    const x = X_MIN + (i / N) * (X_MAX - X_MIN);
    const y = x * x;
    if (y < Y_MIN - 5 || y > Y_MAX + 5) continue;
    pts.push(`${xToPx(x).toFixed(2)},${yToPx(y).toFixed(2)}`);
  }
  return pts.join(' ');
};

// Easing
const easeInOutCubic = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);

// Compute current q (x-coord of Q) by easing between stage start values.
// During stage i, q animates from the *previous* stage's value to Q_VALUES[i].
const currentQ = (frame: number) => {
  if (frame >= NUM_STAGES * STAGE_FRAMES) return Q_VALUES[NUM_STAGES - 1];
  const stage = Math.floor(frame / STAGE_FRAMES);
  const local = frame - stage * STAGE_FRAMES;
  // ease across the first 70% of the stage, dwell on the result for the last 30%
  const t = Math.min(1, local / (STAGE_FRAMES * 0.7));
  const tt = easeInOutCubic(t);
  const qFrom = stage === 0 ? Q_VALUES[0] : Q_VALUES[stage - 1];
  const qTo = Q_VALUES[stage];
  return qFrom + (qTo - qFrom) * tt;
};

// Extend a line through two points (P, Q) to fill the plot rectangle.
// Returns endpoints (in pixel space) clipped to the plot frame.
const extendLineToPlot = (
  px1: number,
  py1: number,
  px2: number,
  py2: number
): [number, number, number, number] => {
  const dx = px2 - px1;
  const dy = py2 - py1;
  if (Math.abs(dx) < 1e-6) {
    return [px1, 0, px1, PLOT_H];
  }
  const slope = dy / dx;
  // Line: py = py1 + slope * (px - px1)
  const candidates: { px: number; py: number }[] = [];
  // Intersect with x = 0 and x = PLOT_W
  const yAt0 = py1 + slope * (0 - px1);
  candidates.push({ px: 0, py: yAt0 });
  const yAtW = py1 + slope * (PLOT_W - px1);
  candidates.push({ px: PLOT_W, py: yAtW });
  // Intersect with y = 0 and y = PLOT_H
  if (Math.abs(slope) > 1e-6) {
    const xAt0 = px1 + (0 - py1) / slope;
    candidates.push({ px: xAt0, py: 0 });
    const xAtH = px1 + (PLOT_H - py1) / slope;
    candidates.push({ px: xAtH, py: PLOT_H });
  }
  // Keep only points that lie on the plot border
  const eps = 0.5;
  const onBorder = candidates.filter(
    (c) => c.px >= -eps && c.px <= PLOT_W + eps && c.py >= -eps && c.py <= PLOT_H + eps
  );
  // Take the two extreme points (the segment that fully spans the plot)
  if (onBorder.length < 2) {
    return [px1, py1, px2, py2];
  }
  // Sort by px (any ordering works for drawing a line)
  onBorder.sort((a, b) => a.px - b.px);
  const a = onBorder[0];
  const b = onBorder[onBorder.length - 1];
  return [a.px, a.py, b.px, b.py];
};

export const SecantToTangentScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Title pop-in
  const titleScale = spring({ frame, fps, config: PAI_THEME.animation.springDefault });
  const titleOpacity = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: 'clamp' });

  // Current Q
  const q = currentQ(frame);
  const m = slopeAt(q); // exact secant slope

  // P and Q in pixel space
  const P_px = xToPx(1);
  const P_py = yToPx(1);
  const Q_px = xToPx(q);
  const Q_py = yToPx(q * q);

  // Active stage (for pill highlighting)
  const stageIdx = Math.min(NUM_STAGES - 1, Math.floor(frame / STAGE_FRAMES));

  // Outro: derivative formula reveal
  const outroFrame = Math.max(0, frame - NUM_STAGES * STAGE_FRAMES);
  const formulaOpacity = interpolate(outroFrame, [0, OUTRO_FRAMES], [0, 1], {
    extrapolateRight: 'clamp',
  });

  // Tangent line glow: appears once we're close to q ≈ 1.
  // Note: interpolate requires a monotonically *increasing* input range, so
  // we flip the mapping (output range from 1→0 as q goes from 1.05→1.5).
  const tangentGlow = interpolate(q, [1.05, 1.5], [1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  // Build the secant line clipped to the plot
  const [sx1, sy1, sx2, sy2] = extendLineToPlot(P_px, P_py, Q_px, Q_py);

  // Build the *true* tangent line at P (slope 2) clipped to the plot
  // Tangent passes through P with slope 2 in math space.
  // In pixel space, slope_px = -slope_math * (yScale / xScale).
  // Easier: choose another point on the tangent, e.g. (1 + 1, 1 + 2*1) = (2, 3) in math space.
  const T_px = xToPx(2);
  const T_py = yToPx(3);
  const [tx1, ty1, tx2, ty2] = extendLineToPlot(P_px, P_py, T_px, T_py);

  return (
    <AbsoluteFill
      style={{
        backgroundColor: PAI_THEME.colors.background,
        padding: 40,
        flexDirection: 'column',
        justifyContent: 'flex-start',
        alignItems: 'center',
        fontFamily: PAI_THEME.typography.fontFamily,
      }}
    >
      {/* Title */}
      <h1
        style={{
          fontSize: 56,
          color: PAI_THEME.colors.text,
          margin: '12px 0 4px',
          opacity: titleOpacity,
          transform: `scale(${titleScale})`,
          textAlign: 'center',
        }}
      >
        Secant → Tangent
      </h1>
      <p
        style={{
          fontSize: 26,
          color: PAI_THEME.colors.accentLight,
          margin: '0 0 12px',
          fontStyle: 'italic',
        }}
      >
        Definition of the derivative as a limit of slopes,&nbsp; on&nbsp; y = x²&nbsp; at&nbsp; P = (1, 1)
      </p>

      {/* Stage pills */}
      <div
        style={{
          display: 'flex',
          gap: 14,
          marginBottom: 8,
          flexWrap: 'wrap',
          justifyContent: 'center',
        }}
      >
        {Q_VALUES.map((qv, i) => {
          const active = i === stageIdx;
          const past = i < stageIdx;
          return (
            <div
              key={i}
              style={{
                padding: '8px 14px',
                borderRadius: 8,
                background: active ? PAI_THEME.colors.accent : 'transparent',
                color: active
                  ? 'white'
                  : past
                  ? PAI_THEME.colors.accentLight
                  : PAI_THEME.colors.textMuted,
                fontSize: 18,
                fontWeight: active ? 600 : 400,
                border: `1px solid ${active ? PAI_THEME.colors.accent : PAI_THEME.colors.textDark}`,
              }}
            >
              q = {qv.toFixed(2)} &nbsp;→&nbsp; slope {(qv + 1).toFixed(2)}
            </div>
          );
        })}
      </div>

      {/* Live readout of current q and slope */}
      <div
        style={{
          color: PAI_THEME.colors.textMuted,
          fontSize: 24,
          marginBottom: 14,
          height: 32,
        }}
      >
        Q = ({q.toFixed(3)}, {(q * q).toFixed(3)}) &nbsp;|&nbsp; secant slope&nbsp;
        <span style={{ color: PAI_THEME.colors.accentLight, fontWeight: 600 }}>
          {m.toFixed(3)}
        </span>
        &nbsp;→&nbsp; limit&nbsp;
        <span style={{ color: PAI_THEME.colors.warning, fontWeight: 600 }}>2</span>
      </div>

      <div
        style={{
          background: PAI_THEME.colors.backgroundAlt,
          borderRadius: 16,
          padding: 16,
        }}
      >
        <svg width={PLOT_W} height={PLOT_H}>
          {/* unit grid */}
          {Array.from({ length: 5 }, (_, i) => i).map((g) => (
            <line
              key={`vg-${g}`}
              x1={xToPx(g)}
              y1={0}
              x2={xToPx(g)}
              y2={PLOT_H}
              stroke="#1e293b"
              strokeWidth={1}
            />
          ))}
          {Array.from({ length: 6 }, (_, i) => i * 2).map((g) => (
            <line
              key={`hg-${g}`}
              x1={0}
              y1={yToPx(g)}
              x2={PLOT_W}
              y2={yToPx(g)}
              stroke="#1e293b"
              strokeWidth={1}
            />
          ))}

          {/* main axes */}
          <line
            x1={0}
            y1={yToPx(0)}
            x2={PLOT_W}
            y2={yToPx(0)}
            stroke={PAI_THEME.colors.textDark}
            strokeWidth={2}
          />
          <line
            x1={xToPx(0)}
            y1={0}
            x2={xToPx(0)}
            y2={PLOT_H}
            stroke={PAI_THEME.colors.textDark}
            strokeWidth={2}
          />

          {/* axis ticks */}
          {[0, 1, 2, 3].map((x) => (
            <text
              key={`xt-${x}`}
              x={xToPx(x)}
              y={yToPx(0) + 28}
              fontSize={22}
              fill={PAI_THEME.colors.textMuted}
              textAnchor="middle"
            >
              {x}
            </text>
          ))}
          {[2, 4, 6, 8].map((y) => (
            <text
              key={`yt-${y}`}
              x={xToPx(0) - 14}
              y={yToPx(y) + 8}
              fontSize={22}
              fill={PAI_THEME.colors.textMuted}
              textAnchor="end"
            >
              {y}
            </text>
          ))}

          {/* parabola y = x² */}
          <polyline
            points={buildParabolaPath()}
            fill="none"
            stroke={PAI_THEME.colors.info}
            strokeWidth={5}
            strokeLinecap="round"
          />

          {/* True tangent at P (drawn faintly always; brightens as Q → P) */}
          <line
            x1={tx1}
            y1={ty1}
            x2={tx2}
            y2={ty2}
            stroke={PAI_THEME.colors.warning}
            strokeWidth={4}
            strokeDasharray="10 8"
            opacity={0.25 + 0.65 * tangentGlow}
          />

          {/* Current secant PQ extended to plot edges */}
          <line
            x1={sx1}
            y1={sy1}
            x2={sx2}
            y2={sy2}
            stroke={PAI_THEME.colors.accent}
            strokeWidth={5}
            strokeLinecap="round"
            opacity={1 - 0.55 * tangentGlow}
          />

          {/* Connector segment from P to Q (visual emphasis) */}
          <line
            x1={P_px}
            y1={P_py}
            x2={Q_px}
            y2={Q_py}
            stroke={PAI_THEME.colors.accentLight}
            strokeWidth={3}
            opacity={0.85}
          />

          {/* Right-triangle Δx, Δy guide (only while Q noticeably differs from P) */}
          {q > 1.04 && (
            <g opacity={0.5}>
              <line
                x1={P_px}
                y1={P_py}
                x2={Q_px}
                y2={P_py}
                stroke={PAI_THEME.colors.textMuted}
                strokeWidth={2}
                strokeDasharray="6 6"
              />
              <line
                x1={Q_px}
                y1={P_py}
                x2={Q_px}
                y2={Q_py}
                stroke={PAI_THEME.colors.textMuted}
                strokeWidth={2}
                strokeDasharray="6 6"
              />
              <text
                x={(P_px + Q_px) / 2}
                y={P_py - 14}
                fontSize={22}
                fill={PAI_THEME.colors.textMuted}
                textAnchor="middle"
              >
                Δx = {(q - 1).toFixed(2)}
              </text>
              <text
                x={Q_px + 14}
                y={(P_py + Q_py) / 2}
                fontSize={22}
                fill={PAI_THEME.colors.textMuted}
              >
                Δy = {(q * q - 1).toFixed(2)}
              </text>
            </g>
          )}

          {/* P marker */}
          <circle
            cx={P_px}
            cy={P_py}
            r={14}
            fill={PAI_THEME.colors.warning}
            stroke="white"
            strokeWidth={3}
          />
          <text
            x={P_px - 24}
            y={P_py + 8}
            fontSize={28}
            fontWeight={700}
            fill={PAI_THEME.colors.warning}
            textAnchor="end"
          >
            P (1, 1)
          </text>

          {/* Q marker */}
          <circle
            cx={Q_px}
            cy={Q_py}
            r={12}
            fill={PAI_THEME.colors.accent}
            stroke="white"
            strokeWidth={3}
          />
          <text
            x={Q_px + 18}
            y={Q_py - 14}
            fontSize={26}
            fontWeight={700}
            fill={PAI_THEME.colors.accent}
          >
            Q
          </text>

          {/* Slope readout near the secant midpoint */}
          <g>
            <rect
              x={20}
              y={20}
              width={360}
              height={86}
              rx={12}
              fill={PAI_THEME.colors.background}
              stroke={PAI_THEME.colors.accent}
              strokeWidth={2}
              opacity={0.92}
            />
            <text
              x={36}
              y={50}
              fontSize={22}
              fill={PAI_THEME.colors.textMuted}
              fontFamily={PAI_THEME.typography.fontFamilyMono}
            >
              secant slope = (q² − 1)/(q − 1)
            </text>
            <text
              x={36}
              y={82}
              fontSize={26}
              fill={PAI_THEME.colors.accentLight}
              fontFamily={PAI_THEME.typography.fontFamilyMono}
              fontWeight={700}
            >
              = q + 1 = {m.toFixed(3)}
            </text>
          </g>
        </svg>
      </div>

      {/* Outro: derivative formula */}
      <div
        style={{
          marginTop: 22,
          color: PAI_THEME.colors.text,
          fontSize: 30,
          opacity: formulaOpacity,
          textAlign: 'center',
          maxWidth: 1500,
        }}
      >
        f'(1) ={' '}
        <span style={{ color: PAI_THEME.colors.accentLight }}>
          lim<sub style={{ fontSize: 18 }}>q → 1</sub>
        </span>
        &nbsp;
        <span style={{ fontFamily: PAI_THEME.typography.fontFamilyMono }}>
          (q² − 1)/(q − 1)
        </span>
        &nbsp;=&nbsp;
        <span style={{ color: PAI_THEME.colors.accentLight }}>lim (q + 1)</span>
        &nbsp;=&nbsp;
        <span style={{ color: PAI_THEME.colors.warning, fontWeight: 700 }}>2</span>
      </div>
    </AbsoluteFill>
  );
};
