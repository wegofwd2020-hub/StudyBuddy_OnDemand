/**
 * NewtonSecondScene — F = m a, demonstrated live.
 *
 * A 2 kg block is pushed by three different forces in sequence (4 N, 8 N, 12 N).
 * For each phase the live force vector, acceleration vector, and velocity vector
 * are drawn on the block, with numeric readouts. Below the block, the v(t) graph
 * traces in real time, showing the slope (acceleration) change at each phase
 * boundary.
 *
 * Frames @ 30fps (26 s = 780 frames):
 *   0–60     title + equation fade in
 *   60–240   Phase A: F = 4 N → a = 2 m/s²  (6 s of physics)
 *   240–420  Phase B: F = 8 N → a = 4 m/s²  (6 s)
 *   420–600  Phase C: F = 12 N → a = 6 m/s² (6 s)
 *   600–720  freeze frame, summary equations
 *   720–780  caption fade
 */
import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate, useVideoConfig, spring } from 'remotion';
import { PAI_THEME } from '../theme';
import { PlotFrame, xToPx, yToPx, buildPath, type Plot } from '../plot';

// ── Physics constants ──────────────────────────────────────────────────────
const MASS_KG = 2;
const PHASE_LEN_FRAMES = 180;     // 6 s at 30 fps
const PHASE_LEN_S = 6;
const T_PHASE_A_START = 60;
const T_PHASE_B_START = T_PHASE_A_START + PHASE_LEN_FRAMES;   // 240
const T_PHASE_C_START = T_PHASE_B_START + PHASE_LEN_FRAMES;   // 420
const T_PHASE_C_END = T_PHASE_C_START + PHASE_LEN_FRAMES;     // 600
const T_SUMMARY_START = T_PHASE_C_END;
const T_CAPTION_START = 720;

// Forces (N) and accelerations (m/s²) per phase
const PHASE_A_F = 4;
const PHASE_B_F = 8;
const PHASE_C_F = 12;
const PHASE_A_A = PHASE_A_F / MASS_KG;   // 2
const PHASE_B_A = PHASE_B_F / MASS_KG;   // 4
const PHASE_C_A = PHASE_C_F / MASS_KG;   // 6

// Velocities at phase boundaries (start of each phase)
const V_AT_A_START = 0;
const V_AT_B_START = V_AT_A_START + PHASE_A_A * PHASE_LEN_S;  // 12
const V_AT_C_START = V_AT_B_START + PHASE_B_A * PHASE_LEN_S;  // 36
const V_AT_C_END = V_AT_C_START + PHASE_C_A * PHASE_LEN_S;    // 72

// Visual scale factors (px per N, px per (m/s²))
const F_PX_PER_N = 18;        // 12 N → 216 px
const A_PX_PER_MS2 = 36;      // 6 m/s² → 216 px
const V_PX_PER_MS = 4;        // 72 m/s → 288 px

// ── Helpers ────────────────────────────────────────────────────────────────
function getPhase(t: number): { F: number; a: number; v: number; label: string } {
  // t = physics seconds since motion began
  if (t < PHASE_LEN_S) {
    return {
      F: PHASE_A_F,
      a: PHASE_A_A,
      v: V_AT_A_START + PHASE_A_A * t,
      label: 'A',
    };
  }
  if (t < 2 * PHASE_LEN_S) {
    return {
      F: PHASE_B_F,
      a: PHASE_B_A,
      v: V_AT_B_START + PHASE_B_A * (t - PHASE_LEN_S),
      label: 'B',
    };
  }
  const tau = Math.min(t - 2 * PHASE_LEN_S, PHASE_LEN_S);
  return {
    F: PHASE_C_F,
    a: PHASE_C_A,
    v: V_AT_C_START + PHASE_C_A * tau,
    label: 'C',
  };
}

export const NewtonSecondScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // ── Timing ───────────────────────────────────────────────────────────────
  const titleScale = spring({ frame, fps, config: PAI_THEME.animation.springDefault });
  const titleOp = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: 'clamp' });
  const subOp = interpolate(frame, [20, 60], [0, 1], { extrapolateRight: 'clamp' });
  const captionOp = interpolate(frame, [T_CAPTION_START, T_CAPTION_START + 60], [0, 1], { extrapolateRight: 'clamp' });

  // Physics-time (seconds since motion began)
  const motionFrame = Math.max(0, Math.min(frame - T_PHASE_A_START, T_PHASE_C_END - T_PHASE_A_START));
  const t = motionFrame / fps;
  const { F, a, v, label } = getPhase(Math.min(t, 3 * PHASE_LEN_S));

  // ── Block geometry ───────────────────────────────────────────────────────
  // Block sits on a horizontal "floor" line. Block stays roughly centered horizontally
  // during the demo (we display its motion via the velocity vector, not by translating
  // off-screen — keeps the FBD readable).
  const floorY = 540;
  const blockY = floorY - 80;  // top of block
  const blockSize = 160;
  const blockX = 700; // top-left x of block, fixed for the visual

  const blockCenterX = blockX + blockSize / 2;
  const blockCenterY = blockY + blockSize / 2;

  // Vector lengths (in px, animated)
  const fLen = F * F_PX_PER_N;
  const aLen = a * A_PX_PER_MS2;
  const vLen = v * V_PX_PER_MS;

  // ── Velocity-time plot ───────────────────────────────────────────────────
  const PW = 1700, PH = 320;
  const plot: Plot = {
    width: PW, height: PH,
    pad: { l: 110, r: 60, t: 30, b: 80 },
    xRange: [0, 18],
    yRange: [0, 80],
    xTicks: [0, 6, 12, 18],
    yTicks: [0, 20, 40, 60, 80],
    xLabel: 't (seconds)',
    yLabel: 'v (m/s)',
  };

  // Reveal fraction (how much of the v-curve to show so far)
  const reveal = Math.max(0, Math.min(t / 18, 1));

  // v(t) function for the curve (piecewise linear)
  const vOfT = (tt: number): number => {
    const tc = Math.max(0, Math.min(tt, 3 * PHASE_LEN_S));
    return getPhase(tc).v;
  };

  // ── Render ───────────────────────────────────────────────────────────────
  return (
    <AbsoluteFill style={{
      background: `linear-gradient(135deg, ${PAI_THEME.colors.background}, ${PAI_THEME.colors.backgroundAlt})`,
      flexDirection: 'column', alignItems: 'center', padding: 30,
      fontFamily: PAI_THEME.typography.fontFamily,
    }}>
      <h1 style={{
        fontSize: 56, color: PAI_THEME.colors.text, margin: '12px 0 4px',
        opacity: titleOp, transform: `scale(${titleScale})`, textAlign: 'center',
      }}>
        Newton's Second Law: F = m a
      </h1>
      <p style={{
        fontSize: 26, color: PAI_THEME.colors.accentLight, margin: '0 0 8px',
        opacity: subOp, fontStyle: 'italic',
      }}>
        Same 2 kg block · three different pushes · slope of v(t) reveals a
      </p>

      {/* Phase pill */}
      <div style={{
        marginTop: 8, marginBottom: 4, display: 'flex', gap: 24,
        opacity: subOp, fontSize: 24, color: PAI_THEME.colors.text,
      }}>
        <span style={{
          padding: '8px 22px', borderRadius: 18,
          background: frame >= T_PHASE_A_START && frame < T_PHASE_B_START
            ? PAI_THEME.colors.info : PAI_THEME.colors.backgroundAlt,
          border: `1.5px solid ${PAI_THEME.colors.textDark}`,
          fontWeight: frame >= T_PHASE_A_START && frame < T_PHASE_B_START ? 700 : 400,
        }}>Phase A: F = 4 N</span>
        <span style={{
          padding: '8px 22px', borderRadius: 18,
          background: frame >= T_PHASE_B_START && frame < T_PHASE_C_START
            ? PAI_THEME.colors.warning : PAI_THEME.colors.backgroundAlt,
          color: frame >= T_PHASE_B_START && frame < T_PHASE_C_START
            ? PAI_THEME.colors.background : PAI_THEME.colors.text,
          border: `1.5px solid ${PAI_THEME.colors.textDark}`,
          fontWeight: frame >= T_PHASE_B_START && frame < T_PHASE_C_START ? 700 : 400,
        }}>Phase B: F = 8 N</span>
        <span style={{
          padding: '8px 22px', borderRadius: 18,
          background: frame >= T_PHASE_C_START
            ? PAI_THEME.colors.error : PAI_THEME.colors.backgroundAlt,
          border: `1.5px solid ${PAI_THEME.colors.textDark}`,
          fontWeight: frame >= T_PHASE_C_START ? 700 : 400,
        }}>Phase C: F = 12 N</span>
      </div>

      {/* Block + arrows */}
      <svg width={1800} height={620} style={{ marginTop: 10 }}>
        <defs>
          <marker id="ns-arr-F" markerWidth={14} markerHeight={14} refX={11} refY={5} orient="auto">
            <polygon points="0,0 12,5 0,10" fill={PAI_THEME.colors.info} />
          </marker>
          <marker id="ns-arr-a" markerWidth={14} markerHeight={14} refX={11} refY={5} orient="auto">
            <polygon points="0,0 12,5 0,10" fill={PAI_THEME.colors.success} />
          </marker>
          <marker id="ns-arr-v" markerWidth={14} markerHeight={14} refX={11} refY={5} orient="auto">
            <polygon points="0,0 12,5 0,10" fill={PAI_THEME.colors.warning} />
          </marker>
        </defs>

        {/* Floor */}
        <line x1={120} y1={floorY} x2={1680} y2={floorY}
          stroke={PAI_THEME.colors.textMuted} strokeWidth={3} />
        {/* Floor hatching */}
        {Array.from({ length: 30 }).map((_, i) => (
          <line key={`h${i}`}
            x1={140 + i * 50} y1={floorY}
            x2={120 + i * 50} y2={floorY + 18}
            stroke={PAI_THEME.colors.textDark} strokeWidth={1.5} />
        ))}

        {/* Block */}
        {frame >= T_PHASE_A_START && (
          <>
            <rect x={blockX} y={blockY} width={blockSize} height={blockSize}
              rx={10} ry={10}
              fill={PAI_THEME.colors.accent} stroke={PAI_THEME.colors.accentDark} strokeWidth={4} />
            <text x={blockCenterX} y={blockCenterY + 14}
              fill={PAI_THEME.colors.text} fontSize={56} fontWeight={700} textAnchor="middle">
              2 kg
            </text>
          </>
        )}

        {/* Force vector F (right of block, blue) */}
        {frame >= T_PHASE_A_START && fLen > 0 && (
          <>
            <line x1={blockCenterX} y1={blockCenterY - 24} x2={blockCenterX + fLen} y2={blockCenterY - 24}
              stroke={PAI_THEME.colors.info} strokeWidth={8} strokeLinecap="round" markerEnd="url(#ns-arr-F)" />
            <text x={blockCenterX + fLen + 18} y={blockCenterY - 14}
              fill={PAI_THEME.colors.info} fontSize={32} fontWeight={700}>
              F = {F.toFixed(0)} N
            </text>
          </>
        )}

        {/* Acceleration vector a (above block, green) */}
        {frame >= T_PHASE_A_START && aLen > 0 && (
          <>
            <line x1={blockCenterX} y1={blockY - 50} x2={blockCenterX + aLen} y2={blockY - 50}
              stroke={PAI_THEME.colors.success} strokeWidth={6} strokeLinecap="round" markerEnd="url(#ns-arr-a)" />
            <text x={blockCenterX + aLen + 16} y={blockY - 40}
              fill={PAI_THEME.colors.success} fontSize={28} fontWeight={700}>
              a = {a.toFixed(0)} m/s²
            </text>
          </>
        )}

        {/* Velocity vector v (below block, amber) */}
        {frame >= T_PHASE_A_START && vLen > 0 && (
          <>
            <line x1={blockCenterX} y1={blockY + blockSize + 50} x2={blockCenterX + Math.min(vLen, 700)} y2={blockY + blockSize + 50}
              stroke={PAI_THEME.colors.warning} strokeWidth={6} strokeLinecap="round" markerEnd="url(#ns-arr-v)" />
            <text x={blockCenterX + Math.min(vLen, 700) + 16} y={blockY + blockSize + 60}
              fill={PAI_THEME.colors.warning} fontSize={28} fontWeight={700}>
              v = {v.toFixed(1)} m/s
            </text>
          </>
        )}

        {/* Live arithmetic readout to the left of the block */}
        {frame >= T_PHASE_A_START && (
          <g>
            <rect x={140} y={blockY - 40} width={500} height={blockSize + 80}
              rx={14} fill={PAI_THEME.colors.backgroundAlt}
              stroke={PAI_THEME.colors.textDark} strokeWidth={2} />
            <text x={390} y={blockY - 5} fill={PAI_THEME.colors.text}
              fontSize={28} fontWeight={700} textAnchor="middle">
              Phase {label}
            </text>
            <text x={170} y={blockY + 40} fill={PAI_THEME.colors.info} fontSize={32} fontWeight={700}>
              F  = {F.toFixed(0)} N
            </text>
            <text x={170} y={blockY + 88} fill={PAI_THEME.colors.text} fontSize={28}>
              m  = 2 kg
            </text>
            <text x={170} y={blockY + 130} fill={PAI_THEME.colors.success} fontSize={32} fontWeight={700}>
              a  = F / m  = {a.toFixed(0)} m/s²
            </text>
            <text x={170} y={blockY + 178} fill={PAI_THEME.colors.warning} fontSize={28} fontWeight={700}>
              v(t) = {v.toFixed(1)} m/s
            </text>
          </g>
        )}
      </svg>

      {/* v–t plot */}
      <svg width={PW} height={PH} style={{ marginTop: 8 }}>
        <PlotFrame p={plot} title="Velocity vs time — slope = a (changes at phase boundary)" />

        {/* The traced curve so far */}
        <polyline
          points={buildPath(plot, vOfT, [0, 18], reveal, 360)}
          fill="none" stroke={PAI_THEME.colors.warning} strokeWidth={5} strokeLinecap="round" />

        {/* Phase boundary vertical guides */}
        <line x1={xToPx(plot, 6)} y1={plot.pad.t} x2={xToPx(plot, 6)} y2={plot.pad.t + plot.height - plot.pad.t - plot.pad.b}
          stroke={PAI_THEME.colors.textDark} strokeWidth={1.5} strokeDasharray="6 6" />
        <line x1={xToPx(plot, 12)} y1={plot.pad.t} x2={xToPx(plot, 12)} y2={plot.pad.t + plot.height - plot.pad.t - plot.pad.b}
          stroke={PAI_THEME.colors.textDark} strokeWidth={1.5} strokeDasharray="6 6" />

        {/* Live cursor */}
        {t > 0 && t < 18 && (
          <>
            <line x1={xToPx(plot, t)} y1={plot.pad.t}
              x2={xToPx(plot, t)} y2={plot.pad.t + plot.height - plot.pad.t - plot.pad.b}
              stroke={PAI_THEME.colors.accent} strokeWidth={2.5} />
            <circle cx={xToPx(plot, t)} cy={yToPx(plot, v)} r={11}
              fill={PAI_THEME.colors.accent} stroke={PAI_THEME.colors.text} strokeWidth={3} />
          </>
        )}
      </svg>

      {/* Caption */}
      <div style={{
        marginTop: 14, color: PAI_THEME.colors.text, fontSize: 28,
        opacity: captionOp, textAlign: 'center', maxWidth: 1700,
      }}>
        Bigger force → steeper v-line → bigger acceleration. With m fixed, a is proportional to F.
      </div>
    </AbsoluteFill>
  );
};
