/**
 * SingleSlitDiffractionScene — sinc² pattern + animated slit width sweep.
 *
 * Setup:
 *   - Vertical slit on the left with parametric width a
 *   - Light fan after the slit (visualised as opacity wedge)
 *   - Vertical screen on the right showing the sinc²(π·a·sin θ / λ) intensity profile
 *   - Slit width sweeps narrow → wide; central peak inversely scales
 *
 * Frames @ 30fps (24 s = 720 frames):
 *   0–60     title fade
 *   60–180   slit appears at a = 1.0× λ (3 s)
 *   180–540  slit width sweeps 1× λ → 4× λ (12 s) — central peak narrows visibly
 *   540–720  hold final tableau with annotation (6 s)
 */
import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate, useVideoConfig, spring } from 'remotion';
import { PAI_THEME } from '../theme';

const F_TITLE_END = 60;
const F_SLIT_IN = 180;
const F_SWEEP_END = 540;
const F_END = 720;

const SLIT_X = 480;
const SLIT_CENTER_Y = 540;
const SCREEN_X = 1500;
const SCREEN_TOP = 220;
const SCREEN_BOTTOM = 860;
const SCREEN_HEIGHT = SCREEN_BOTTOM - SCREEN_TOP;

const LAMBDA_PX = 100; // visual scale: 1 wavelength = 100 px in slit-width units

// sinc²(u) = (sin(πu)/(πu))²
function sinc2(u: number): number {
  if (Math.abs(u) < 1e-9) return 1;
  const x = Math.PI * u;
  return (Math.sin(x) / x) ** 2;
}

export const SingleSlitDiffractionScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const titleScale = spring({ frame, fps, config: PAI_THEME.animation.springDefault });
  const titleOp = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: 'clamp' });
  const subOp = interpolate(frame, [20, 60], [0, 1], { extrapolateRight: 'clamp' });
  const sceneOp = interpolate(frame, [60, F_SLIT_IN], [0, 1], { extrapolateRight: 'clamp' });

  // Slit-width parameter a (in units of λ). Sweep 1.0 → 4.0.
  let aOverLambda: number;
  if (frame < F_SLIT_IN) {
    aOverLambda = 1.0;
  } else if (frame < F_SWEEP_END) {
    const t = (frame - F_SLIT_IN) / (F_SWEEP_END - F_SLIT_IN);
    aOverLambda = 1.0 + (4.0 - 1.0) * t;
  } else {
    aOverLambda = 4.0;
  }
  const slitHalfH = (aOverLambda * LAMBDA_PX) / 2;

  // Intensity profile sinc²(a·sin θ / λ); use y on screen as a proxy for sin θ
  // We treat y in [-1, 1] over the screen height, with (a/λ) controlling first-zero position.
  // First zero at y_zero such that (a/λ) · y_zero = 1  →  y_zero = λ/a (relative).
  // Visual scaling: the screen spans y_rel in [-2, 2] (multiples of λ/a × first-zero-distance).
  const samples = 200;
  const profilePoints: { y: number; intensity: number }[] = [];
  for (let i = 0; i <= samples; i++) {
    const yRel = -2 + (i / samples) * 4; // from -2 to +2 (in units of λ/a … sort of)
    const u = aOverLambda * yRel * 0.5;
    const intensity = sinc2(u);
    const yPx = SCREEN_TOP + ((yRel + 2) / 4) * SCREEN_HEIGHT;
    profilePoints.push({ y: yPx, intensity });
  }

  const annotationOp = interpolate(frame, [F_SWEEP_END, F_SWEEP_END + 60], [0, 1], { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' });

  return (
    <AbsoluteFill style={{
      background: `linear-gradient(135deg, ${PAI_THEME.colors.background}, ${PAI_THEME.colors.backgroundAlt})`,
      fontFamily: PAI_THEME.typography.fontFamily,
    }}>
      <div style={{ position: 'absolute', top: 30, left: 0, right: 0, textAlign: 'center' }}>
        <h1 style={{
          fontSize: 56, color: PAI_THEME.colors.text, margin: 0,
          opacity: titleOp, transform: `scale(${titleScale})`,
        }}>
          Single-Slit Diffraction — Slit Width Drives Pattern Width
        </h1>
        <p style={{
          fontSize: 26, color: PAI_THEME.colors.accentLight, marginTop: 6, fontStyle: 'italic',
          opacity: subOp,
        }}>
          Narrower slit → wider central peak. Wider slit → tighter peak. Watch them swap.
        </p>
      </div>

      <svg width={1920} height={1080} viewBox="0 0 1920 1080" style={{ position: 'absolute', inset: 0, opacity: sceneOp }}>
        {/* Slit barrier */}
        <rect x={SLIT_X - 8} y={120} width={16} height={SLIT_CENTER_Y - slitHalfH - 120}
          fill={PAI_THEME.colors.surface} />
        <rect x={SLIT_X - 8} y={SLIT_CENTER_Y + slitHalfH} width={16} height={960 - (SLIT_CENTER_Y + slitHalfH)}
          fill={PAI_THEME.colors.surface} />

        {/* Slit width annotation */}
        <line x1={SLIT_X - 40} y1={SLIT_CENTER_Y - slitHalfH} x2={SLIT_X - 40} y2={SLIT_CENTER_Y + slitHalfH}
          stroke={PAI_THEME.colors.warning} strokeWidth={3} />
        <line x1={SLIT_X - 50} y1={SLIT_CENTER_Y - slitHalfH} x2={SLIT_X - 30} y2={SLIT_CENTER_Y - slitHalfH}
          stroke={PAI_THEME.colors.warning} strokeWidth={3} />
        <line x1={SLIT_X - 50} y1={SLIT_CENTER_Y + slitHalfH} x2={SLIT_X - 30} y2={SLIT_CENTER_Y + slitHalfH}
          stroke={PAI_THEME.colors.warning} strokeWidth={3} />
        <text x={SLIT_X - 60} y={SLIT_CENTER_Y + 8} fill={PAI_THEME.colors.warning}
          fontSize={28} fontWeight={700} textAnchor="end">a</text>
        <text x={SLIT_X - 60} y={SLIT_CENTER_Y + 38} fill={PAI_THEME.colors.warning}
          fontSize={22} fontWeight={700} textAnchor="end">{aOverLambda.toFixed(1)} λ</text>

        {/* Light fan after slit (opacity wedge) */}
        <defs>
          <linearGradient id="light-fan" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor={PAI_THEME.colors.bright} stopOpacity={0.5} />
            <stop offset="100%" stopColor={PAI_THEME.colors.bright} stopOpacity={0.05} />
          </linearGradient>
        </defs>
        <polygon
          points={`${SLIT_X},${SLIT_CENTER_Y - slitHalfH} ${SLIT_X},${SLIT_CENTER_Y + slitHalfH} ${SCREEN_X},${SCREEN_BOTTOM} ${SCREEN_X},${SCREEN_TOP}`}
          fill="url(#light-fan)" />

        {/* Incoming light arrow on the left */}
        <line x1={120} y1={SLIT_CENTER_Y} x2={SLIT_X - 60} y2={SLIT_CENTER_Y}
          stroke={PAI_THEME.colors.bright} strokeWidth={4} />
        <polygon points={`${SLIT_X - 60},${SLIT_CENTER_Y} ${SLIT_X - 75},${SLIT_CENTER_Y - 8} ${SLIT_X - 75},${SLIT_CENTER_Y + 8}`}
          fill={PAI_THEME.colors.bright} />
        <text x={140} y={SLIT_CENTER_Y - 16} fill={PAI_THEME.colors.bright}
          fontSize={22} fontWeight={700}>incoming light · wavelength λ</text>

        {/* Screen */}
        <rect x={SCREEN_X - 12} y={SCREEN_TOP} width={24} height={SCREEN_HEIGHT}
          fill="#0f172a" stroke={PAI_THEME.colors.surface} strokeWidth={2} />
        <text x={SCREEN_X} y={SCREEN_TOP - 14}
          fill={PAI_THEME.colors.surface} fontSize={22} fontWeight={700} textAnchor="middle">screen</text>

        {/* Pattern on screen as colour-modulated bands */}
        {profilePoints.map((p, i) => {
          if (i === profilePoints.length - 1) return null;
          const next = profilePoints[i + 1];
          const avg = (p.intensity + next.intensity) / 2;
          return (
            <rect key={i}
              x={SCREEN_X - 12} y={p.y}
              width={24} height={next.y - p.y}
              fill={`rgba(251, 191, 36, ${avg.toFixed(3)})`} />
          );
        })}

        {/* Intensity profile plot to the right of screen */}
        <line x1={SCREEN_X + 30} y1={SCREEN_TOP} x2={SCREEN_X + 30} y2={SCREEN_BOTTOM}
          stroke={PAI_THEME.colors.surface} strokeWidth={1.5} />
        <text x={SCREEN_X + 30} y={SCREEN_TOP - 14}
          fill={PAI_THEME.colors.surface} fontSize={18} fontWeight={700} textAnchor="middle">intensity</text>
        <polyline
          points={profilePoints.map((p) => `${SCREEN_X + 30 + p.intensity * 280},${p.y}`).join(' ')}
          fill="none" stroke={PAI_THEME.colors.bright} strokeWidth={3} />

        {/* Annotation: first minimum line */}
        {annotationOp > 0 && (
          <g opacity={annotationOp}>
            <text x={SCREEN_X + 320} y={screenCenterY(SCREEN_TOP, SCREEN_BOTTOM, 1 / aOverLambda)}
              fill={PAI_THEME.colors.success} fontSize={20} fontWeight={700}>
              first minimum
            </text>
            <text x={SCREEN_X + 320} y={screenCenterY(SCREEN_TOP, SCREEN_BOTTOM, 1 / aOverLambda) + 22}
              fill={PAI_THEME.colors.success} fontSize={16}>
              sin θ = λ/a
            </text>
          </g>
        )}

        <text x={960} y={1010} fill={PAI_THEME.colors.text}
          fontSize={26} fontWeight={700} textAnchor="middle">
          The narrower the slit relative to λ, the more dramatically light spreads after it.
        </text>
      </svg>
    </AbsoluteFill>
  );
};

function screenCenterY(top: number, bottom: number, frac: number): number {
  // map frac (positive direction) to screen y near the centre
  const center = (top + bottom) / 2;
  return center - frac * (bottom - top) * 0.25;
}
