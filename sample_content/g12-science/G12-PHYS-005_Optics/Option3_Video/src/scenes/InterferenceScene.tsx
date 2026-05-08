/**
 * InterferenceScene — two coherent sources emitting circular wavefronts.
 *
 * Layout:
 *   - Two source dots (A, B) on the left, separated by distance d
 *   - Circular wavefronts continuously expand from each at the same period
 *   - A vertical screen on the right captures the resulting fringe pattern
 *   - Intensity profile (cos²) on the screen builds up over time
 *
 * Frames @ 30fps (24 s = 720 frames):
 *   0–60     title fade
 *   60–150   sources appear, first wavefronts emerge (3 s)
 *   150–540  steady-state wavefront propagation (13 s) — pattern builds on screen
 *   540–720  hold final tableau with fringe-spacing annotation (6 s)
 */
import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate, useVideoConfig, spring } from 'remotion';
import { PAI_THEME } from '../theme';

// ── Geometry ──────────────────────────────────────────────────────────────
const SOURCE_X = 360;
const SOURCE_A_Y = 480;
const SOURCE_B_Y = 600;
const SCREEN_X = 1500;
const SCREEN_TOP = 220;
const SCREEN_BOTTOM = 860;

// Wavefront speed and emission period
const WAVE_SPEED = 80;          // px / s
const WAVE_PERIOD = 0.4;        // s — emit a new wavefront every 0.4 s
const F_TITLE_END = 60;
const F_WAVES_START = 90;
const F_END = 720;

export const InterferenceScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const titleScale = spring({ frame, fps, config: PAI_THEME.animation.springDefault });
  const titleOp = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: 'clamp' });
  const subOp = interpolate(frame, [20, 60], [0, 1], { extrapolateRight: 'clamp' });
  const sceneOp = interpolate(frame, [60, F_WAVES_START], [0, 1], { extrapolateRight: 'clamp' });

  const t = Math.max(0, (frame - F_WAVES_START) / fps);

  // Compute all wavefronts emitted so far
  const lastN = Math.floor(t / WAVE_PERIOD);
  const wavesA: { r: number; opacity: number }[] = [];
  const wavesB: { r: number; opacity: number }[] = [];
  for (let n = 0; n <= lastN; n++) {
    const te = n * WAVE_PERIOD;
    const r = WAVE_SPEED * (t - te);
    if (r > 1300) continue;
    const opacity = Math.max(0.18, 1 - r / 1300 * 0.7);
    wavesA.push({ r, opacity });
    wavesB.push({ r, opacity });
  }

  // Build intensity profile on the screen.
  // Approximate Young's: at point (SCREEN_X, y), path difference = (distance from B) − (distance from A).
  // Bright when path diff = nλ; intensity ~ cos²(π · path_diff / λ).
  // Use λ that matches WAVE_SPEED * WAVE_PERIOD for self-consistency: λ = 80 * 0.4 = 32 px.
  const lambda = WAVE_SPEED * WAVE_PERIOD;
  const fringePoints: { y: number; intensity: number }[] = [];
  const N_SAMPLES = 60;
  for (let i = 0; i <= N_SAMPLES; i++) {
    const y = SCREEN_TOP + (i / N_SAMPLES) * (SCREEN_BOTTOM - SCREEN_TOP);
    const dA = Math.hypot(SCREEN_X - SOURCE_X, y - SOURCE_A_Y);
    const dB = Math.hypot(SCREEN_X - SOURCE_X, y - SOURCE_B_Y);
    const pathDiff = dB - dA;
    const intensity = Math.cos(Math.PI * pathDiff / lambda) ** 2;
    fringePoints.push({ y, intensity });
  }
  // Pattern build-up — intensity scales from 0 to 1 over frames 90 to 540
  const buildUp = interpolate(frame, [F_WAVES_START, 540], [0, 1], { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' });
  const annotationOp = interpolate(frame, [600, 660], [0, 1], { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' });

  // Find first two adjacent maxima for Δy annotation
  const fringeYs: number[] = [];
  for (let i = 1; i < fringePoints.length - 1; i++) {
    if (fringePoints[i].intensity > fringePoints[i - 1].intensity && fringePoints[i].intensity > fringePoints[i + 1].intensity && fringePoints[i].intensity > 0.85) {
      fringeYs.push(fringePoints[i].y);
    }
  }

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
          Two-Source Interference — Fringes Emerge
        </h1>
        <p style={{
          fontSize: 26, color: PAI_THEME.colors.accentLight, marginTop: 6, fontStyle: 'italic',
          opacity: subOp,
        }}>
          Two coherent sources. Wavefronts overlap. The screen records bright and dark bands.
        </p>
      </div>

      <svg width={1920} height={1080} viewBox="0 0 1920 1080" style={{ position: 'absolute', inset: 0, opacity: sceneOp }}>
        {/* Wavefronts from source A */}
        {wavesA.map((w, i) => (
          <circle key={`a${i}`} cx={SOURCE_X} cy={SOURCE_A_Y} r={w.r}
            fill="none" stroke={PAI_THEME.colors.sourceA} strokeWidth={2.5} opacity={w.opacity} />
        ))}
        {/* Wavefronts from source B */}
        {wavesB.map((w, i) => (
          <circle key={`b${i}`} cx={SOURCE_X} cy={SOURCE_B_Y} r={w.r}
            fill="none" stroke={PAI_THEME.colors.sourceB} strokeWidth={2.5} opacity={w.opacity} />
        ))}

        {/* Source dots */}
        <circle cx={SOURCE_X} cy={SOURCE_A_Y} r={16} fill={PAI_THEME.colors.sourceA} stroke={PAI_THEME.colors.text} strokeWidth={2.5} />
        <text x={SOURCE_X - 30} y={SOURCE_A_Y + 6} fill={PAI_THEME.colors.sourceA} fontSize={26} fontWeight={700} textAnchor="end">A</text>
        <circle cx={SOURCE_X} cy={SOURCE_B_Y} r={16} fill={PAI_THEME.colors.sourceB} stroke={PAI_THEME.colors.text} strokeWidth={2.5} />
        <text x={SOURCE_X - 30} y={SOURCE_B_Y + 6} fill={PAI_THEME.colors.sourceB} fontSize={26} fontWeight={700} textAnchor="end">B</text>

        {/* Source separation label */}
        <line x1={SOURCE_X - 40} y1={SOURCE_A_Y} x2={SOURCE_X - 40} y2={SOURCE_B_Y}
          stroke={PAI_THEME.colors.warning} strokeWidth={2} />
        <text x={SOURCE_X - 56} y={(SOURCE_A_Y + SOURCE_B_Y) / 2}
          fill={PAI_THEME.colors.warning} fontSize={24} fontWeight={700} textAnchor="end">d</text>

        {/* Screen */}
        <rect x={SCREEN_X - 12} y={SCREEN_TOP} width={24} height={SCREEN_BOTTOM - SCREEN_TOP}
          fill="#0f172a" stroke={PAI_THEME.colors.surface} strokeWidth={2} />
        <text x={SCREEN_X} y={SCREEN_TOP - 14}
          fill={PAI_THEME.colors.surface} fontSize={22} fontWeight={700} textAnchor="middle">screen</text>

        {/* Render fringes on the screen + intensity profile to the right */}
        {fringePoints.map((p, i) => {
          if (i === fringePoints.length - 1) return null;
          const next = fringePoints[i + 1];
          const avg = (p.intensity + next.intensity) / 2 * buildUp;
          return (
            <rect key={i}
              x={SCREEN_X - 12} y={p.y}
              width={24} height={next.y - p.y}
              fill={`rgba(251, 191, 36, ${avg.toFixed(3)})`} />
          );
        })}

        {/* Intensity profile to the right of the screen */}
        <line x1={SCREEN_X + 30} y1={SCREEN_TOP} x2={SCREEN_X + 30} y2={SCREEN_BOTTOM}
          stroke={PAI_THEME.colors.surface} strokeWidth={1.5} />
        <text x={SCREEN_X + 30} y={SCREEN_TOP - 14} fill={PAI_THEME.colors.surface}
          fontSize={18} fontWeight={700} textAnchor="middle">intensity</text>
        <polyline
          points={fringePoints.map((p) => `${SCREEN_X + 30 + p.intensity * 250 * buildUp},${p.y}`).join(' ')}
          fill="none" stroke={PAI_THEME.colors.bright} strokeWidth={3} />

        {/* Δy annotation */}
        {fringeYs.length >= 2 && annotationOp > 0 && (
          <g opacity={annotationOp}>
            <line x1={SCREEN_X - 40} y1={fringeYs[0]} x2={SCREEN_X - 40} y2={fringeYs[1]}
              stroke={PAI_THEME.colors.success} strokeWidth={2.5} />
            <line x1={SCREEN_X - 50} y1={fringeYs[0]} x2={SCREEN_X - 30} y2={fringeYs[0]}
              stroke={PAI_THEME.colors.success} strokeWidth={2.5} />
            <line x1={SCREEN_X - 50} y1={fringeYs[1]} x2={SCREEN_X - 30} y2={fringeYs[1]}
              stroke={PAI_THEME.colors.success} strokeWidth={2.5} />
            <text x={SCREEN_X - 60} y={(fringeYs[0] + fringeYs[1]) / 2 + 6}
              fill={PAI_THEME.colors.success} fontSize={24} fontWeight={700} textAnchor="end">Δy</text>
          </g>
        )}

        {/* Caption */}
        <text x={960} y={1010} fill={PAI_THEME.colors.text}
          fontSize={26} fontWeight={700} textAnchor="middle">
          Constructive overlap = bright. Destructive overlap = dark. Spacing Δy = λL/d.
        </text>
      </svg>
    </AbsoluteFill>
  );
};
