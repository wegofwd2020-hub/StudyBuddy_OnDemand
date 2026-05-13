/**
 * RollerCoasterScene — energy conservation visualised.
 *
 * A 500 kg cart traverses a track that has four key heights:
 *   A: top of first hill           h = 40 m  (start, at rest)
 *   B: bottom of dip               h =  0 m  (KE_max)
 *   C: top of second hill          h = 20 m
 *   D: end of run                  h =  5 m
 *
 * The track is sampled at N points; height h(s) is a smooth piecewise sinusoid
 * passing through A → B → C → D so the physics integrates cleanly.
 *
 * Phase 1 (0 – 14 s) — frictionless run.
 *   At every position, KE = E_total − m g h(s).  Speed v = √(2·KE/m).
 *   The cart is positioned by integrating ds = v dt along the track.
 *   The bar chart on the right shows KE (blue) + PE (green) summing to a
 *   constant 196 kJ.
 *
 * Phase 2 (16 – 30 s) — same track, with friction.
 *   A constant non-conservative drag removes 4 kJ per metre travelled, so
 *   the total mechanical energy bar visibly shrinks as the cart moves.
 *   Cart slows progressively; if energy < required PE for next hill, it
 *   stops on the slope (we never let v² go negative).
 *
 * Frames @ 30 fps (32 s = 960 frames):
 *    0–60     title fade in
 *   60–480    Phase 1: frictionless traversal A → D (~14 s of physics)
 *  480–540    pause + label "Now add friction"
 *  540–900    Phase 2: same track, with friction (~12 s of physics)
 *  900–960    summary caption fade
 */
import React from 'react';
import {
  AbsoluteFill,
  useCurrentFrame,
  interpolate,
  useVideoConfig,
  spring,
} from 'remotion';
import { PAI_THEME } from '../theme';

// ── Physics constants ──────────────────────────────────────────────────────
const MASS_KG = 500;
const G = 9.8;

// Heights in metres at each key point along the track.
const H_A = 40;
const H_B = 0;
const H_C = 20;
const H_D = 5;

// Track key points in normalised s ∈ [0, 1]
const S_A = 0.0;
const S_B = 0.34;
const S_C = 0.66;
const S_D = 1.0;

// Total mechanical energy at start (frictionless reference).
const E_TOTAL_J = MASS_KG * G * H_A; // 500 · 9.8 · 40 = 196 000 J

// Friction strength: kJ removed per metre of track travelled in Phase 2.
const TRACK_LENGTH_M = 100; // approximate path length (purely for friction scaling)
const FRICTION_J_PER_M = 700; // → 70 kJ over 100 m, leaves 126 kJ at the end
// Calibrated so the cart still makes it over hill C (which needs PE = 98 kJ
// at s ≈ 0.66 → distance 66 m → lost 46.2 kJ → remaining 149.8 kJ > 98 kJ).

// ── Scene timing ───────────────────────────────────────────────────────────
const FPS = 30;
const T_TITLE_FRAMES = 60;
const PHASE_1_FRAMES = 420; // 14 s
const T_PHASE_1_END = T_TITLE_FRAMES + PHASE_1_FRAMES; // 480
const T_PAUSE_END = T_PHASE_1_END + 60; // 540
const PHASE_2_FRAMES = 360; // 12 s
const T_PHASE_2_END = T_PAUSE_END + PHASE_2_FRAMES; // 900
const T_CAPTION_START = T_PHASE_2_END;

// ── Track geometry ─────────────────────────────────────────────────────────
// Height in metres as a function of s ∈ [0, 1].
// Use cubic-ease segments between A → B → C → D so derivatives are smooth.
function heightAt(s: number): number {
  if (s <= S_A) return H_A;
  if (s >= S_D) return H_D;
  // s in [S_A, S_B] → A to B   (down)
  if (s <= S_B) {
    const u = (s - S_A) / (S_B - S_A);
    const eased = 0.5 - 0.5 * Math.cos(Math.PI * u); // 0 → 1, smooth
    return H_A + (H_B - H_A) * eased;
  }
  // s in [S_B, S_C] → B to C   (up)
  if (s <= S_C) {
    const u = (s - S_B) / (S_C - S_B);
    const eased = 0.5 - 0.5 * Math.cos(Math.PI * u);
    return H_B + (H_C - H_B) * eased;
  }
  // s in [S_C, S_D] → C to D   (down small)
  const u = (s - S_C) / (S_D - S_C);
  const eased = 0.5 - 0.5 * Math.cos(Math.PI * u);
  return H_C + (H_D - H_C) * eased;
}

// ── Visual layout ──────────────────────────────────────────────────────────
const TRACK_X0 = 200;
const TRACK_X1 = 1280;
const TRACK_LEN_PX = TRACK_X1 - TRACK_X0; // 1080 px wide
const TRACK_Y0 = 760;     // y-pixel of h = 0
const H_PX_PER_M = 12;    // 40 m of height → 480 px tall

const BAR_X = 1430;
const BAR_TOP_Y = 200;
const BAR_BOTTOM_Y = 760;
const BAR_FULL_PX = BAR_BOTTOM_Y - BAR_TOP_Y; // 560 px = 196 kJ
const BAR_WIDTH = 90;

function trackXFromS(s: number) {
  return TRACK_X0 + s * TRACK_LEN_PX;
}
function trackYFromH(h: number) {
  return TRACK_Y0 - h * H_PX_PER_M;
}

// Slope (radians) at parameter s — used for cart tilt.
// Returns the angle of the tangent in screen coordinates (y-down), so a
// positive value rotates the cart clockwise — nose down.
function slopeAngle(s: number): number {
  const ds = 0.001;
  const s0 = Math.max(0, s - ds);
  const s1 = Math.min(1, s + ds);
  const dx = (s1 - s0) * TRACK_LEN_PX;
  // In screen coords, Y increases downward, while heightAt grows upward.
  // dy_screen = -(heightAt(s1) - heightAt(s0)) * H_PX_PER_M
  const dy = -(heightAt(s1) - heightAt(s0)) * H_PX_PER_M;
  return Math.atan2(dy, dx);
}

// ── Pre-integrate position vs frame ────────────────────────────────────────
// We need s(frame) for each phase. Speed depends on remaining KE; integrate
// numerically once at module load.
//
// The "physics-time" mapping: we want the cart to traverse the whole track in
// PHASE_1_PHYSICS_S seconds (Phase 1) and PHASE_2_PHYSICS_S seconds (Phase 2)
// of physics-time. We scale ds/dt by (real-track-length-m / chosen-time) so the
// pacing fits the scene budget.
//
// Strategy: take the actual energy-conserving v(s), normalise it, then
// proportionally scale so that ∫ds/v over [0,1] = chosen physics duration.
//
// v_unit(s) = √(2 (E − m g h(s)) / m) — proportional to physical speed.
// Total time at unit pacing: T_unit = ∫₀¹ ds / v_unit(s) (numerical).
// Pacing factor: k = T_chosen / T_unit. Use ds/dt_real = v_unit / k.

const PHASE_1_PHYSICS_S = 14;
const PHASE_2_PHYSICS_S = 12;

const SAMPLES = 1000;

function vUnitFrictionless(s: number): number {
  const ke = Math.max(0, E_TOTAL_J - MASS_KG * G * heightAt(s));
  return Math.sqrt((2 * ke) / MASS_KG);
}

function vUnitWithFriction(s: number, sStart = 0): number {
  // Energy at start = E_TOTAL_J. After travelling pathLength(sStart→s) metres,
  // friction has removed FRICTION_J_PER_M · m_travelled.
  // Approximate path length linearly along s for simplicity (cart speed scales
  // to mask the geometric inaccuracy; energy conservation is still exact in s).
  const sTravelled = Math.max(0, s - sStart);
  const distM = sTravelled * TRACK_LENGTH_M;
  const eRemaining = E_TOTAL_J - FRICTION_J_PER_M * distM;
  const ke = Math.max(0, eRemaining - MASS_KG * G * heightAt(s));
  return Math.sqrt((2 * ke) / MASS_KG);
}

// Build a frame → s lookup table for each phase.
function buildPhaseTable(
  totalFrames: number,
  vUnitFn: (s: number) => number,
  physicsSeconds: number,
): Float64Array {
  // Step 1: compute T_unit = ∫₀¹ ds / v_unit(s). Tiny clamp to avoid div by zero.
  const eps = 1e-3;
  let tUnit = 0;
  for (let i = 0; i < SAMPLES; i++) {
    const s = (i + 0.5) / SAMPLES;
    const v = Math.max(eps, vUnitFn(s));
    tUnit += (1 / SAMPLES) / v;
  }
  const k = physicsSeconds / tUnit;

  // Step 2: integrate ds/dt = vUnit / k vs frame (dt = 1/fps).
  const table = new Float64Array(totalFrames + 1);
  let s = 0;
  for (let f = 0; f <= totalFrames; f++) {
    table[f] = Math.min(1, s);
    const v = Math.max(eps, vUnitFn(s)) / k; // ds/dt in s-units per second
    s += v * (1 / FPS);
    if (s > 1) s = 1;
  }
  return table;
}

const PHASE_1_TABLE = buildPhaseTable(
  PHASE_1_FRAMES,
  vUnitFrictionless,
  PHASE_1_PHYSICS_S,
);
const PHASE_2_TABLE = buildPhaseTable(
  PHASE_2_FRAMES,
  (s) => vUnitWithFriction(s, 0),
  PHASE_2_PHYSICS_S,
);

// ── Helpers ────────────────────────────────────────────────────────────────
function getCartState(frame: number): {
  s: number;
  h: number;
  ke: number;
  pe: number;
  eTotal: number; // total mechanical energy remaining (drops in phase 2)
  v: number;
  phase: 'title' | 'p1' | 'pause' | 'p2' | 'caption';
  withFriction: boolean;
} {
  if (frame < T_TITLE_FRAMES) {
    return {
      s: 0,
      h: H_A,
      ke: 0,
      pe: E_TOTAL_J,
      eTotal: E_TOTAL_J,
      v: 0,
      phase: 'title',
      withFriction: false,
    };
  }
  if (frame < T_PHASE_1_END) {
    const idx = frame - T_TITLE_FRAMES;
    const s = PHASE_1_TABLE[idx] ?? 1;
    const h = heightAt(s);
    const pe = MASS_KG * G * h;
    const ke = Math.max(0, E_TOTAL_J - pe);
    const v = Math.sqrt((2 * ke) / MASS_KG);
    return {
      s, h, ke, pe, eTotal: E_TOTAL_J, v,
      phase: 'p1', withFriction: false,
    };
  }
  if (frame < T_PAUSE_END) {
    return {
      s: 1,
      h: H_D,
      ke: Math.max(0, E_TOTAL_J - MASS_KG * G * H_D),
      pe: MASS_KG * G * H_D,
      eTotal: E_TOTAL_J,
      v: 0,
      phase: 'pause',
      withFriction: false,
    };
  }
  if (frame < T_PHASE_2_END) {
    const idx = frame - T_PAUSE_END;
    const s = PHASE_2_TABLE[idx] ?? 1;
    const h = heightAt(s);
    const distM = s * TRACK_LENGTH_M;
    const eRemaining = Math.max(0, E_TOTAL_J - FRICTION_J_PER_M * distM);
    const pe = MASS_KG * G * h;
    const ke = Math.max(0, eRemaining - pe);
    const v = Math.sqrt((2 * ke) / MASS_KG);
    return {
      s, h, ke, pe, eTotal: eRemaining, v,
      phase: 'p2', withFriction: true,
    };
  }
  // caption / final
  const distM = TRACK_LENGTH_M;
  const eRemaining = Math.max(0, E_TOTAL_J - FRICTION_J_PER_M * distM);
  const pe = MASS_KG * G * H_D;
  const ke = Math.max(0, eRemaining - pe);
  return {
    s: 1, h: H_D, ke, pe, eTotal: eRemaining, v: Math.sqrt((2 * ke) / MASS_KG),
    phase: 'caption', withFriction: true,
  };
}

// ── Track polyline (precompute path string) ───────────────────────────────
function buildTrackPath(): string {
  const N = 200;
  const pts: string[] = [];
  for (let i = 0; i <= N; i++) {
    const s = i / N;
    const x = trackXFromS(s).toFixed(1);
    const y = trackYFromH(heightAt(s)).toFixed(1);
    pts.push(`${i === 0 ? 'M' : 'L'} ${x} ${y}`);
  }
  return pts.join(' ');
}
const TRACK_PATH = buildTrackPath();

// ── Cart shape ─────────────────────────────────────────────────────────────
const CART_W = 64;
const CART_H = 36;

const Cart: React.FC<{ x: number; y: number; angleRad: number }> = ({
  x, y, angleRad,
}) => {
  const angleDeg = (angleRad * 180) / Math.PI;
  return (
    <g transform={`translate(${x} ${y}) rotate(${angleDeg})`}>
      {/* Body */}
      <rect
        x={-CART_W / 2}
        y={-CART_H - 4}
        width={CART_W}
        height={CART_H}
        rx={6}
        fill={PAI_THEME.colors.error}
        stroke={PAI_THEME.colors.text}
        strokeWidth={2}
      />
      {/* Stripe */}
      <rect
        x={-CART_W / 2 + 4}
        y={-CART_H - 4 + 6}
        width={CART_W - 8}
        height={5}
        fill={PAI_THEME.colors.warning}
      />
      {/* Wheels */}
      <circle cx={-CART_W / 2 + 12} cy={-2} r={6} fill={PAI_THEME.colors.text} />
      <circle cx={CART_W / 2 - 12} cy={-2} r={6} fill={PAI_THEME.colors.text} />
    </g>
  );
};

// ── Scene component ────────────────────────────────────────────────────────
export const RollerCoasterScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  void fps;

  const titleScale = spring({
    frame, fps: FPS, config: PAI_THEME.animation.springDefault,
  });
  const titleOp = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: 'clamp' });
  const subOp = interpolate(frame, [20, 60], [0, 1], { extrapolateRight: 'clamp' });

  const state = getCartState(frame);

  // Cart screen position
  const cartX = trackXFromS(state.s);
  const cartY = trackYFromH(state.h);
  const cartAngle = slopeAngle(state.s);

  // Bar chart: KE blue (bottom), PE green (top of stack), Lost-to-friction
  // amber zone above (only in Phase 2 — the "shrunk" region of the bar).
  const peHeightPx = (state.pe / E_TOTAL_J) * BAR_FULL_PX;
  const keHeightPx = (state.ke / E_TOTAL_J) * BAR_FULL_PX;
  const lostHeightPx = ((E_TOTAL_J - state.eTotal) / E_TOTAL_J) * BAR_FULL_PX;

  // Bar layout, top→bottom:
  //   [lost band]  (BAR_TOP_Y .. BAR_TOP_Y + lostHeightPx)
  //   [PE band]    (BAR_TOP_Y + lostHeightPx .. + peHeightPx)
  //   [KE band]    (...        .. BAR_BOTTOM_Y)
  const lostY = BAR_TOP_Y;
  const peY = BAR_TOP_Y + lostHeightPx;
  const keY = peY + peHeightPx;
  // sanity: keY + keHeightPx should equal BAR_BOTTOM_Y (within rounding).

  // Phase banner pill colours
  const phase1Active = state.phase === 'p1';
  const phase2Active = state.phase === 'p2';
  const pauseActive = state.phase === 'pause';

  const captionOp = interpolate(
    frame, [T_CAPTION_START, T_CAPTION_START + 45],
    [0, 1], { extrapolateRight: 'clamp' },
  );

  // Pause label
  const pauseLabelOp = pauseActive
    ? interpolate(
      frame, [T_PHASE_1_END, T_PHASE_1_END + 15],
      [0, 1], { extrapolateRight: 'clamp' },
    )
    : 0;

  return (
    <AbsoluteFill style={{
      background: `linear-gradient(135deg, ${PAI_THEME.colors.background}, ${PAI_THEME.colors.backgroundAlt})`,
      flexDirection: 'column',
      alignItems: 'center',
      padding: 30,
      fontFamily: PAI_THEME.typography.fontFamily,
    }}>
      <h1 style={{
        fontSize: 56,
        color: PAI_THEME.colors.text,
        margin: '12px 0 4px',
        opacity: titleOp,
        transform: `scale(${titleScale})`,
        textAlign: 'center',
      }}>
        Roller-Coaster Energy:  KE + PE = constant
      </h1>
      <p style={{
        fontSize: 26,
        color: PAI_THEME.colors.accentLight,
        margin: '0 0 8px',
        opacity: subOp,
        fontStyle: 'italic',
      }}>
        500 kg cart · four checkpoints · the bar chart never lies
      </p>

      {/* Phase pills */}
      <div style={{
        marginTop: 8, marginBottom: 6, display: 'flex', gap: 24,
        opacity: subOp, fontSize: 22, color: PAI_THEME.colors.text,
      }}>
        <span style={{
          padding: '8px 22px', borderRadius: 18,
          background: phase1Active ? PAI_THEME.colors.info : PAI_THEME.colors.backgroundAlt,
          border: `1.5px solid ${PAI_THEME.colors.textDark}`,
          fontWeight: phase1Active ? 700 : 400,
        }}>
          Phase 1 · frictionless
        </span>
        <span style={{
          padding: '8px 22px', borderRadius: 18,
          background: phase2Active ? PAI_THEME.colors.error : PAI_THEME.colors.backgroundAlt,
          border: `1.5px solid ${PAI_THEME.colors.textDark}`,
          fontWeight: phase2Active ? 700 : 400,
        }}>
          Phase 2 · with friction
        </span>
      </div>

      <svg width={1860} height={830} style={{ marginTop: 4 }}>
        <defs>
          <linearGradient id="rc-sky" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#1e293b" />
            <stop offset="100%" stopColor="#0f172a" />
          </linearGradient>
        </defs>

        {/* Sky / scene panel */}
        <rect x={120} y={140} width={1240} height={660}
          fill="url(#rc-sky)" stroke={PAI_THEME.colors.textDark} strokeWidth={1.5} rx={14} />

        {/* Ground reference dashed line at h = 0 */}
        <line
          x1={TRACK_X0 - 30} y1={trackYFromH(0)}
          x2={TRACK_X1 + 30} y2={trackYFromH(0)}
          stroke={PAI_THEME.colors.textMuted}
          strokeWidth={1.4}
          strokeDasharray="6 6"
        />
        <text x={TRACK_X0 - 36} y={trackYFromH(0) + 6}
          fill={PAI_THEME.colors.textMuted} fontSize={20} textAnchor="end">
          h = 0
        </text>

        {/* Height grid: every 10 m */}
        {[10, 20, 30, 40].map((h) => (
          <g key={`hg-${h}`}>
            <line
              x1={TRACK_X0 - 30} y1={trackYFromH(h)}
              x2={TRACK_X1 + 30} y2={trackYFromH(h)}
              stroke="#1e293b"
              strokeWidth={1}
              strokeDasharray="3 6"
            />
            <text x={TRACK_X0 - 36} y={trackYFromH(h) + 6}
              fill={PAI_THEME.colors.textDark} fontSize={18} textAnchor="end">
              {h} m
            </text>
          </g>
        ))}

        {/* Track */}
        <path d={TRACK_PATH} fill="none"
          stroke={PAI_THEME.colors.accent} strokeWidth={6}
          strokeLinecap="round" strokeLinejoin="round" />

        {/* Track support struts: drop verticals every ~7 samples to ground */}
        {Array.from({ length: 21 }).map((_, i) => {
          const s = i / 20;
          const tx = trackXFromS(s);
          const ty = trackYFromH(heightAt(s));
          if (Math.abs(ty - trackYFromH(0)) < 4) return null;
          return (
            <line key={`strut-${i}`}
              x1={tx} y1={ty}
              x2={tx} y2={trackYFromH(0)}
              stroke={PAI_THEME.colors.textDark}
              strokeWidth={1} opacity={0.5} />
          );
        })}

        {/* Checkpoint markers A B C D */}
        {[
          { s: S_A, label: 'A', h: H_A },
          { s: S_B, label: 'B', h: H_B },
          { s: S_C, label: 'C', h: H_C },
          { s: S_D, label: 'D', h: H_D },
        ].map((p) => (
          <g key={`cp-${p.label}`}>
            <circle
              cx={trackXFromS(p.s)} cy={trackYFromH(p.h)} r={9}
              fill={PAI_THEME.colors.warning}
              stroke={PAI_THEME.colors.text} strokeWidth={2.5}
            />
            <text
              x={trackXFromS(p.s)}
              y={trackYFromH(p.h) + (p.label === 'B' ? 32 : -16)}
              fill={PAI_THEME.colors.text}
              fontSize={26} fontWeight={700} textAnchor="middle">
              {p.label}
            </text>
            <text
              x={trackXFromS(p.s)}
              y={trackYFromH(p.h) + (p.label === 'B' ? 52 : -38)}
              fill={PAI_THEME.colors.textMuted}
              fontSize={18} textAnchor="middle">
              h = {p.h} m
            </text>
          </g>
        ))}

        {/* Cart */}
        {(state.phase === 'p1' || state.phase === 'pause' || state.phase === 'p2' || state.phase === 'caption') && (
          <Cart x={cartX} y={cartY} angleRad={cartAngle} />
        )}

        {/* Live readout box */}
        <g>
          <rect x={150} y={170} width={340} height={146} rx={12}
            fill={PAI_THEME.colors.backgroundAlt}
            stroke={PAI_THEME.colors.textDark} strokeWidth={1.6} />
          <text x={170} y={206} fill={PAI_THEME.colors.text}
            fontSize={26} fontWeight={700}>
            Live state
          </text>
          <text x={170} y={240} fill={PAI_THEME.colors.textMuted} fontSize={20}>
            h = <tspan fill={PAI_THEME.colors.text} fontWeight={700}>{state.h.toFixed(1)} m</tspan>
          </text>
          <text x={170} y={266} fill={PAI_THEME.colors.textMuted} fontSize={20}>
            v = <tspan fill={PAI_THEME.colors.warning} fontWeight={700}>{state.v.toFixed(1)} m/s</tspan>
          </text>
          <text x={170} y={292} fill={PAI_THEME.colors.textMuted} fontSize={20}>
            E_total = <tspan
              fill={state.withFriction ? PAI_THEME.colors.error : PAI_THEME.colors.success}
              fontWeight={700}>
              {(state.eTotal / 1000).toFixed(1)} kJ
            </tspan>
          </text>
        </g>

        {/* Pause label */}
        {pauseActive && (
          <g opacity={pauseLabelOp}>
            <rect
              x={620} y={400} width={560} height={120} rx={20}
              fill={PAI_THEME.colors.error}
              stroke={PAI_THEME.colors.text}
              strokeWidth={3} opacity={0.92} />
            <text x={900} y={448}
              fill={PAI_THEME.colors.text}
              fontSize={36} fontWeight={700} textAnchor="middle">
              Now add friction
            </text>
            <text x={900} y={486}
              fill={PAI_THEME.colors.text}
              fontSize={22} textAnchor="middle" fontStyle="italic">
              Total mechanical energy will shrink as the cart moves.
            </text>
          </g>
        )}

        {/* ── Energy bar chart on the right ── */}
        <g>
          {/* Outer frame */}
          <rect
            x={BAR_X - 30} y={BAR_TOP_Y - 60}
            width={BAR_WIDTH + 240}
            height={BAR_FULL_PX + 130} rx={14}
            fill={PAI_THEME.colors.backgroundAlt}
            stroke={PAI_THEME.colors.textDark} strokeWidth={1.6} />

          <text x={BAR_X + BAR_WIDTH / 2} y={BAR_TOP_Y - 22}
            fill={PAI_THEME.colors.text}
            fontSize={26} fontWeight={700} textAnchor="middle">
            Energy (kJ)
          </text>

          {/* Lost-to-friction band (top) */}
          {lostHeightPx > 0.5 && (
            <rect
              x={BAR_X} y={lostY}
              width={BAR_WIDTH} height={lostHeightPx}
              fill={PAI_THEME.colors.warning}
              stroke={PAI_THEME.colors.text} strokeWidth={1.5} />
          )}

          {/* PE band */}
          {peHeightPx > 0.5 && (
            <rect
              x={BAR_X} y={peY}
              width={BAR_WIDTH} height={peHeightPx}
              fill={PAI_THEME.colors.success}
              stroke={PAI_THEME.colors.text} strokeWidth={1.5} />
          )}

          {/* KE band */}
          {keHeightPx > 0.5 && (
            <rect
              x={BAR_X} y={keY}
              width={BAR_WIDTH} height={keHeightPx}
              fill={PAI_THEME.colors.info}
              stroke={PAI_THEME.colors.text} strokeWidth={1.5} />
          )}

          {/* Total reference line at full height */}
          <line
            x1={BAR_X - 12} y1={BAR_TOP_Y}
            x2={BAR_X + BAR_WIDTH + 12} y2={BAR_TOP_Y}
            stroke={PAI_THEME.colors.error} strokeWidth={2} strokeDasharray="6 5" />
          <text x={BAR_X + BAR_WIDTH + 18} y={BAR_TOP_Y + 6}
            fill={PAI_THEME.colors.error} fontSize={18} fontWeight={700}>
            196 kJ start
          </text>

          {/* Numeric labels next to each band */}
          {keHeightPx > 18 && (
            <text
              x={BAR_X + BAR_WIDTH + 18}
              y={keY + keHeightPx / 2 + 7}
              fill={PAI_THEME.colors.info}
              fontSize={20} fontWeight={700}>
              KE  {(state.ke / 1000).toFixed(1)}
            </text>
          )}
          {peHeightPx > 18 && (
            <text
              x={BAR_X + BAR_WIDTH + 18}
              y={peY + peHeightPx / 2 + 7}
              fill={PAI_THEME.colors.success}
              fontSize={20} fontWeight={700}>
              PE  {(state.pe / 1000).toFixed(1)}
            </text>
          )}
          {lostHeightPx > 18 && (
            <text
              x={BAR_X + BAR_WIDTH + 18}
              y={lostY + lostHeightPx / 2 + 7}
              fill={PAI_THEME.colors.warning}
              fontSize={20} fontWeight={700}>
              heat  {((E_TOTAL_J - state.eTotal) / 1000).toFixed(1)}
            </text>
          )}

          {/* y-axis ticks every 50 kJ */}
          {[0, 50, 100, 150, 196].map((kj) => {
            const y = BAR_BOTTOM_Y - (kj / 196) * BAR_FULL_PX;
            return (
              <g key={`tick-${kj}`}>
                <line x1={BAR_X - 8} y1={y} x2={BAR_X} y2={y}
                  stroke={PAI_THEME.colors.textMuted} strokeWidth={1.2} />
                <text x={BAR_X - 14} y={y + 6}
                  fill={PAI_THEME.colors.textMuted} fontSize={16} textAnchor="end">
                  {kj}
                </text>
              </g>
            );
          })}
        </g>
      </svg>

      {/* Caption */}
      <div style={{
        marginTop: 6, color: PAI_THEME.colors.text, fontSize: 28,
        opacity: state.phase === 'caption' ? captionOp : 0,
        textAlign: 'center', maxWidth: 1700,
      }}>
        Frictionless: total energy is fixed — KE and PE just trade.   With friction: the bar literally shrinks.
      </div>
    </AbsoluteFill>
  );
};
