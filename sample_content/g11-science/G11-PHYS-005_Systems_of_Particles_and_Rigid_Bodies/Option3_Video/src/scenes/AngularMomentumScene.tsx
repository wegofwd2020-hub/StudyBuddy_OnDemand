/**
 * AngularMomentumScene — Conservation of angular momentum, demonstrated live.
 *
 * A stylised figure skater spins on frictionless ice. With arms extended she
 * has moment of inertia I_out and angular speed omega_out. Over 4 seconds she
 * pulls her arms in: I drops linearly to I_in (smaller), and ω rises so the
 * product L = Iω stays exactly constant. Live bar charts show I, ω, L, and
 * KE_rot in real time. KE_rot rises because the skater does internal work
 * pulling her arms in — that surplus comes from her muscles, not from L.
 *
 * Frames @ 30 fps (28 s = 840 frames):
 *   0   – 60   title + equation fade in
 *   60  – 180  Phase 1: arms extended, steady spin (4 s)
 *   180 – 300  Phase 2: pulling arms in (4 s)
 *   300 – 480  Phase 3: arms tucked, fast spin (6 s)
 *   480 – 720  steady fast spin + summary (8 s)
 *   720 – 840  caption fade (4 s)
 */
import React from 'react';
import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
} from 'remotion';
import { PAI_THEME } from '../theme';

// ── Physics constants ──────────────────────────────────────────────────────
// Toy-physics units. The numbers are chosen so the bars stay readable and
// the arithmetic is exact.
const I_OUT = 12;          // moment of inertia, arms extended  (units · ·m²)
const I_IN = 4;            // moment of inertia, arms tucked     (factor of 3 less)
const OMEGA_OUT = 2;       // angular speed, arms extended       (rad/s)
// Conservation requires L = I ω constant ⇒ ω_in = I_OUT * OMEGA_OUT / I_IN
const L_CONST = I_OUT * OMEGA_OUT;        // 24
const OMEGA_IN = L_CONST / I_IN;          // 6
// KE_rot at each phase: ½ I ω². Out: 0.5*12*4 = 24. In: 0.5*4*36 = 72.
// (Internal work has tripled KE.)

// ── Phase boundaries (frames) ──────────────────────────────────────────────
const T_TITLE_END = 60;
const T_PHASE_1_END = 180;
const T_PHASE_2_END = 300;
const T_PHASE_3_END = 480;
const T_SUMMARY_START = 480;
const T_CAPTION_START = 720;

// Bar-chart visual scale
const BAR_MAX_HEIGHT = 360;
const I_BAR_DIVISOR = 12;     // I_OUT maps to full height
const OMEGA_BAR_DIVISOR = 6;  // OMEGA_IN maps to full height
const L_BAR_DIVISOR = 24;     // L stays constant at 24 → full height
const KE_BAR_DIVISOR = 72;    // peaks at 72

// ── Helpers ────────────────────────────────────────────────────────────────
function getPhysics(frame: number): {
  I: number;
  omega: number;
  L: number;
  KE: number;
  armLength: number;     // visual arm length (px)
  phaseLabel: string;
} {
  // Compute I across phases. ω is fixed by L conservation (L = I*ω).
  // Phase 1 (60–180): I = I_OUT
  // Phase 2 (180–300): I linearly drops I_OUT → I_IN (4 s, 120 frames)
  // Phase 3+ (≥300): I = I_IN
  let I: number;
  let phaseLabel: string;
  if (frame < T_PHASE_1_END) {
    I = I_OUT;
    phaseLabel = '1: arms extended';
  } else if (frame < T_PHASE_2_END) {
    const frac = (frame - T_PHASE_1_END) / (T_PHASE_2_END - T_PHASE_1_END);
    I = I_OUT + (I_IN - I_OUT) * frac;
    phaseLabel = '2: pulling arms in';
  } else {
    I = I_IN;
    phaseLabel = '3: arms tucked';
  }

  const omega = L_CONST / I;
  const L = I * omega;             // ≡ L_CONST by construction
  const KE = 0.5 * I * omega * omega;

  // Visual arm length: 220 px when extended, 60 px when fully tucked.
  // Map I in [I_IN, I_OUT] to armLength in [60, 220].
  const armLength = 60 + ((I - I_IN) / (I_OUT - I_IN)) * (220 - 60);

  return { I, omega, L, KE, armLength, phaseLabel };
}

// Cumulative rotation angle (radians) — integrate ω numerically frame-by-frame
// from frame 60 onward. Pre-compute by recursion through phase formulas.
function rotationAngleAt(frame: number, fps: number): number {
  if (frame <= T_TITLE_END) return 0;

  const dt = 1 / fps;
  let theta = 0;

  // Phase 1: constant ω = OMEGA_OUT for frames 60..min(frame, T_PHASE_1_END)
  const f1End = Math.min(frame, T_PHASE_1_END);
  theta += OMEGA_OUT * (f1End - T_TITLE_END) * dt;

  // Phase 2: I linear from I_OUT to I_IN, ω = L_CONST / I.
  // Integrate ω·dt over the partial interval inside phase 2.
  if (frame > T_PHASE_1_END) {
    const f2End = Math.min(frame, T_PHASE_2_END);
    const dur = T_PHASE_2_END - T_PHASE_1_END;
    // Simple Euler accumulation in 1-frame steps; cheap and good enough.
    for (let f = T_PHASE_1_END; f < f2End; f++) {
      const frac = (f - T_PHASE_1_END) / dur;
      const I = I_OUT + (I_IN - I_OUT) * frac;
      theta += (L_CONST / I) * dt;
    }
  }

  // Phase 3+: constant ω = OMEGA_IN for frames T_PHASE_2_END..frame
  if (frame > T_PHASE_2_END) {
    theta += OMEGA_IN * (frame - T_PHASE_2_END) * dt;
  }

  return theta;
}

// ── Reusable bar-chart cell ────────────────────────────────────────────────
const Bar: React.FC<{
  x: number;
  baseY: number;
  height: number;
  width: number;
  color: string;
  label: string;
  value: string;
  unit: string;
}> = ({ x, baseY, height, width, color, label, value, unit }) => {
  const safeH = Math.max(0, Math.min(height, BAR_MAX_HEIGHT));
  return (
    <g>
      {/* Track */}
      <rect
        x={x} y={baseY - BAR_MAX_HEIGHT}
        width={width} height={BAR_MAX_HEIGHT}
        rx={6} ry={6}
        fill={PAI_THEME.colors.backgroundAlt}
        stroke={PAI_THEME.colors.textDark} strokeWidth={1.5}
      />
      {/* Filled bar */}
      <rect
        x={x} y={baseY - safeH}
        width={width} height={safeH}
        rx={6} ry={6}
        fill={color} opacity={0.85}
      />
      {/* Label */}
      <text x={x + width / 2} y={baseY + 36}
        fill={PAI_THEME.colors.text} fontSize={28} fontWeight={700} textAnchor="middle">
        {label}
      </text>
      {/* Value */}
      <text x={x + width / 2} y={baseY + 72}
        fill={color} fontSize={32} fontWeight={700} textAnchor="middle">
        {value}
      </text>
      {/* Unit */}
      <text x={x + width / 2} y={baseY + 100}
        fill={PAI_THEME.colors.textMuted} fontSize={20} textAnchor="middle" fontStyle="italic">
        {unit}
      </text>
    </g>
  );
};

// ── Scene ──────────────────────────────────────────────────────────────────
export const AngularMomentumScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Title fade
  const titleScale = spring({ frame, fps, config: PAI_THEME.animation.springDefault });
  const titleOp = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: 'clamp' });
  const subOp = interpolate(frame, [20, 60], [0, 1], { extrapolateRight: 'clamp' });
  const captionOp = interpolate(frame, [T_CAPTION_START, T_CAPTION_START + 60], [0, 1], { extrapolateRight: 'clamp' });
  const summaryOp = interpolate(frame, [T_SUMMARY_START, T_SUMMARY_START + 60], [0, 1], { extrapolateRight: 'clamp' });

  // Live physics
  const { I, omega, L, KE, armLength, phaseLabel } = getPhysics(frame);
  const theta = rotationAngleAt(frame, fps);
  const thetaDeg = (theta * 180) / Math.PI;

  // Skater layout
  const cx = 600;             // skater rotation centre (left third of screen)
  const cy = 560;
  const headR = 36;
  const bodyHeight = 200;     // body length (head-to-feet)

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
        Conservation of Angular Momentum: L = I ω
      </h1>
      <p style={{
        fontSize: 26, color: PAI_THEME.colors.accentLight, margin: '0 0 10px',
        opacity: subOp, fontStyle: 'italic',
      }}>
        Same skater · same ice · arms in → I drops, ω rises, L stays the same
      </p>

      {/* Phase pill */}
      <div style={{
        marginTop: 4, marginBottom: 4,
        padding: '8px 28px', borderRadius: 22,
        background: frame < T_PHASE_1_END
          ? PAI_THEME.colors.info
          : frame < T_PHASE_2_END
            ? PAI_THEME.colors.warning
            : PAI_THEME.colors.error,
        border: `1.5px solid ${PAI_THEME.colors.text}`,
        fontWeight: 700, fontSize: 26, color: PAI_THEME.colors.background,
        opacity: subOp,
      }}>
        Phase {phaseLabel}
      </div>

      {/* Main canvas: skater on left, bars on right */}
      <svg width={1860} height={760} style={{ marginTop: 12 }}>
        <defs>
          <marker id="am-arr-omega" markerWidth={14} markerHeight={14} refX={11} refY={5} orient="auto">
            <polygon points="0,0 12,5 0,10" fill={PAI_THEME.colors.success} />
          </marker>
          <marker id="am-arr-L" markerWidth={14} markerHeight={14} refX={11} refY={5} orient="auto">
            <polygon points="0,0 12,5 0,10" fill={PAI_THEME.colors.accentLight} />
          </marker>
        </defs>

        {/* Ice surface */}
        <line x1={140} y1={cy + 130} x2={1080} y2={cy + 130}
          stroke={PAI_THEME.colors.textMuted} strokeWidth={2.5} />
        {Array.from({ length: 18 }).map((_, i) => (
          <line key={`ice${i}`}
            x1={160 + i * 52} y1={cy + 130}
            x2={140 + i * 52} y2={cy + 148}
            stroke={PAI_THEME.colors.textDark} strokeWidth={1.2} />
        ))}
        <text x={610} y={cy + 174}
          fill={PAI_THEME.colors.textMuted} fontSize={20} fontStyle="italic" textAnchor="middle">
          frictionless ice — no external torque
        </text>

        {/* Vertical rotation axis (dashed, behind skater) */}
        <line x1={cx} y1={cy - 240} x2={cx} y2={cy + 130}
          stroke={PAI_THEME.colors.accent} strokeWidth={2}
          strokeDasharray="8 6" opacity={0.6} />
        <text x={cx + 14} y={cy - 220} fill={PAI_THEME.colors.accent}
          fontSize={20} fontStyle="italic">rotation axis</text>

        {/* Skater. Drawn in a rotated group so the body+arms+head all spin together.
            cx, cy is the rotation pivot. */}
        <g transform={`rotate(${thetaDeg} ${cx} ${cy})`}>
          {/* Trailing leg (slight diagonal) */}
          <line x1={cx} y1={cy + 60} x2={cx + 22} y2={cy + 130}
            stroke={PAI_THEME.colors.text} strokeWidth={5} strokeLinecap="round" />
          {/* Skating leg */}
          <line x1={cx} y1={cy + 60} x2={cx} y2={cy + 130}
            stroke={PAI_THEME.colors.text} strokeWidth={6} strokeLinecap="round" />
          {/* Torso */}
          <line x1={cx} y1={cy - 90} x2={cx} y2={cy + 60}
            stroke={PAI_THEME.colors.text} strokeWidth={8} strokeLinecap="round" />
          {/* Head */}
          <circle cx={cx} cy={cy - 90 - headR} r={headR}
            fill={PAI_THEME.colors.warning} stroke={PAI_THEME.colors.text} strokeWidth={3} />
          {/* Two outstretched arms — length grows/shrinks with phase */}
          <line x1={cx} y1={cy - 60} x2={cx - armLength} y2={cy - 60}
            stroke={PAI_THEME.colors.info} strokeWidth={8} strokeLinecap="round" />
          <circle cx={cx - armLength} cy={cy - 60} r={10}
            fill={PAI_THEME.colors.info} stroke={PAI_THEME.colors.text} strokeWidth={2} />
          <line x1={cx} y1={cy - 60} x2={cx + armLength} y2={cy - 60}
            stroke={PAI_THEME.colors.info} strokeWidth={8} strokeLinecap="round" />
          <circle cx={cx + armLength} cy={cy - 60} r={10}
            fill={PAI_THEME.colors.info} stroke={PAI_THEME.colors.text} strokeWidth={2} />
        </g>

        {/* L vector (drawn outside the rotation, pointing up along the axis).
            L is constant — the arrow is constant length. */}
        <line x1={cx} y1={cy - 280} x2={cx} y2={cy - 410}
          stroke={PAI_THEME.colors.accentLight} strokeWidth={6}
          strokeLinecap="round" markerEnd="url(#am-arr-L)" />
        <text x={cx + 24} y={cy - 360}
          fill={PAI_THEME.colors.accentLight} fontSize={36} fontWeight={700}>
          L (constant)
        </text>

        {/* ω indicator: a circular arrow whose radius is fixed but stroke width
            scales with current ω (visual cue for spin speed). */}
        {(() => {
          const omegaStrokeW = 4 + (omega / OMEGA_IN) * 6;   // 4 .. 10
          // Draw a 270°-arc arrow on the ice level, around the skater's feet.
          const r = 100;
          const cyArc = cy + 130;
          // From angle 30° to 300° (CCW)
          const start = { x: cx + r * Math.cos((30 * Math.PI) / 180), y: cyArc + r * Math.sin((30 * Math.PI) / 180) };
          const end = { x: cx + r * Math.cos((300 * Math.PI) / 180), y: cyArc + r * Math.sin((300 * Math.PI) / 180) };
          const path = `M ${start.x} ${start.y} A ${r} ${r} 0 1 0 ${end.x} ${end.y}`;
          return (
            <>
              <path d={path}
                fill="none" stroke={PAI_THEME.colors.success} strokeWidth={omegaStrokeW}
                strokeLinecap="round" markerEnd="url(#am-arr-omega)" opacity={0.85} />
              <text x={cx} y={cyArc + 24}
                fill={PAI_THEME.colors.success} fontSize={32} fontWeight={700} textAnchor="middle">
                ω = {omega.toFixed(1)} rad/s
              </text>
            </>
          );
        })()}

        {/* ─── Bar chart panel (right) ─── */}
        <g transform={`translate(${1180}, ${0})`}>
          {/* Panel background */}
          <rect x={-20} y={40} width={680} height={680}
            rx={20} fill={PAI_THEME.colors.backgroundAlt}
            stroke={PAI_THEME.colors.textDark} strokeWidth={2} opacity={0.6} />
          <text x={320} y={84} fill={PAI_THEME.colors.text}
            fontSize={36} fontWeight={700} textAnchor="middle">
            Live readouts
          </text>

          {/* Bars */}
          <Bar
            x={0} baseY={520} width={120}
            height={(I / I_BAR_DIVISOR) * BAR_MAX_HEIGHT}
            color={PAI_THEME.colors.info}
            label="I"
            value={I.toFixed(1)}
            unit="kg·m²"
          />
          <Bar
            x={160} baseY={520} width={120}
            height={(omega / OMEGA_BAR_DIVISOR) * BAR_MAX_HEIGHT}
            color={PAI_THEME.colors.success}
            label="ω"
            value={omega.toFixed(2)}
            unit="rad/s"
          />
          <Bar
            x={320} baseY={520} width={120}
            height={(L / L_BAR_DIVISOR) * BAR_MAX_HEIGHT}
            color={PAI_THEME.colors.accentLight}
            label="L = I ω"
            value={L.toFixed(1)}
            unit="kg·m²/s"
          />
          <Bar
            x={480} baseY={520} width={120}
            height={(KE / KE_BAR_DIVISOR) * BAR_MAX_HEIGHT}
            color={PAI_THEME.colors.warning}
            label="½ I ω²"
            value={KE.toFixed(1)}
            unit="J (rot KE)"
          />

          {/* Pinned value of L_CONST as a horizontal reference line on the L bar */}
          <line x1={320} y1={520 - BAR_MAX_HEIGHT}
            x2={440} y2={520 - BAR_MAX_HEIGHT}
            stroke={PAI_THEME.colors.accentLight} strokeWidth={3}
            strokeDasharray="6 6" />
          <text x={444} y={520 - BAR_MAX_HEIGHT + 8}
            fill={PAI_THEME.colors.accentLight} fontSize={18} fontWeight={700}>
            L = 24 (locked)
          </text>

          {/* Summary equations (fade in late) */}
          <g opacity={summaryOp}>
            <line x1={0} y1={644} x2={640} y2={644}
              stroke={PAI_THEME.colors.textDark} strokeWidth={1.5} />
            <text x={320} y={678} fill={PAI_THEME.colors.text}
              fontSize={26} fontWeight={700} textAnchor="middle">
              I × ω = {I.toFixed(1)} × {omega.toFixed(2)} = {L.toFixed(1)}  ✓
            </text>
            <text x={320} y={708} fill={PAI_THEME.colors.warning}
              fontSize={20} textAnchor="middle" fontStyle="italic">
              KE_rot grew from 24 J to {KE.toFixed(0)} J — surplus came from internal muscle work.
            </text>
          </g>
        </g>
      </svg>

      {/* Caption */}
      <div style={{
        marginTop: 8, color: PAI_THEME.colors.text, fontSize: 28,
        opacity: captionOp, textAlign: 'center', maxWidth: 1700,
      }}>
        No external torque on the skater · L stays exactly fixed · the spin speed-up is a free consequence of mass moving toward the axis.
      </div>
    </AbsoluteFill>
  );
};
