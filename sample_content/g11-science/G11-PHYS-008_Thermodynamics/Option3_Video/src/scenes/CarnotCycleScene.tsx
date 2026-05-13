/**
 * CarnotCycleScene — animated traversal of the Carnot cycle on a PV diagram,
 * synchronised with a piston-and-cylinder cartoon and a reservoir indicator.
 *
 * The four states (A, B, C, D) and the analytic curves connecting them are
 * physically consistent:
 *
 *   A: V=1.5, P=4.5   start (hot, compressed)        — at T_H
 *   B: V=2.5, P=2.7   end of isothermal expansion    — at T_H   (PV = 6.75)
 *   C: V=4.0, P=1.43  end of adiabatic expansion     — at T_C   (PV^1.4 = 9.07)
 *   D: V=2.4, P=2.38  end of isothermal compression  — at T_C   (PV = 5.72)
 *   D→A adiabatic compression                                   (PV^1.4 = 8.00)
 *
 * γ = 1.4 (diatomic ideal gas).  The two adiabats are steeper than the two
 * isotherms at any common point, which is the geometric signature of a Carnot
 * cycle on a PV diagram.
 *
 * Frames @ 30 fps (32 s total = 960 frames):
 *   0–60     Title fade in
 *   60–120   Axes + 4 state dots fade in, full cycle outline drawn
 *   120–300  Stroke 1 — isothermal expansion at T_H  (A → B), absorb Q_H
 *   300–480  Stroke 2 — adiabatic expansion          (B → C), cools to T_C
 *   480–660  Stroke 3 — isothermal compression at T_C (C → D), reject Q_C
 *   660–840  Stroke 4 — adiabatic compression        (D → A), heats to T_H
 *   840–960  Efficiency formula + closing caption
 */
import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate, spring, useVideoConfig } from 'remotion';
import { PAI_THEME } from '../theme';

// ─── Plot-area geometry (in SVG pixels) ─────────────────────────────────────
// SVG canvas: 900 × 800; P axis: 1 → 5;  V axis: 1 → 5
const PLOT_W = 900;
const PLOT_H = 800;
const PLOT_LEFT = 100;
const PLOT_RIGHT = 900;
const PLOT_TOP = 100;
const PLOT_BOTTOM = 740;
const V_MIN = 1.0;
const V_MAX = 5.0;
const P_MIN = 1.0;
const P_MAX = 5.0;

const xOf = (V: number) =>
  PLOT_LEFT + ((V - V_MIN) / (V_MAX - V_MIN)) * (PLOT_RIGHT - PLOT_LEFT);
const yOf = (P: number) =>
  PLOT_BOTTOM - ((P - P_MIN) / (P_MAX - P_MIN)) * (PLOT_BOTTOM - PLOT_TOP);

// ─── Carnot state points ────────────────────────────────────────────────────
// Carnot state coordinates chosen so that the cycle closes exactly:
//   isothermal AB:  P_A V_A = P_B V_B  =  6.75
//   adiabatic  BC:  P_B V_B^γ = P_C V_C^γ
//   isothermal CD:  P_C V_C = P_D V_D
//   adiabatic  DA:  P_D V_D^γ = P_A V_A^γ
// The Carnot constraint V_C/V_D = V_B/V_A is built into the choice of D.
const A = { V: 1.5, P: 4.5 };
const B = { V: 2.5, P: 2.7 };
const C = { V: 4.0, P: 1.3983 };
const D = { V: 2.4, P: 2.3305 };
const GAMMA = 1.4;

// PV constants for each leg
const K_AB = A.P * A.V; // 6.75
const K_BC = B.P * Math.pow(B.V, GAMMA); // ~9.07
const K_CD = C.P * C.V; // 5.7144
const K_DA = D.P * Math.pow(D.V, GAMMA); // ~8.00

// ─── Stroke timing (frames at 30fps) ────────────────────────────────────────
const STROKE_LEN = 180;   // frames per stroke (6 s)
const T_TITLE_END = 60;
const T_AXES_END = 120;
const T_STROKE1_END = T_AXES_END + STROKE_LEN;       // 300
const T_STROKE2_END = T_STROKE1_END + STROKE_LEN;    // 480
const T_STROKE3_END = T_STROKE2_END + STROKE_LEN;    // 660
const T_STROKE4_END = T_STROKE3_END + STROKE_LEN;    // 840
const T_TOTAL = T_STROKE4_END + 120;                 // 960

// Sample-points for the four legs (V values to evaluate at; we walk in V)
function sampleIsothermal(Vstart: number, Vend: number, K: number, n: number) {
  const pts: [number, number][] = [];
  for (let i = 0; i <= n; i++) {
    const t = i / n;
    const V = Vstart + (Vend - Vstart) * t;
    const P = K / V;
    pts.push([V, P]);
  }
  return pts;
}
function sampleAdiabatic(Vstart: number, Vend: number, K: number, n: number) {
  const pts: [number, number][] = [];
  for (let i = 0; i <= n; i++) {
    const t = i / n;
    const V = Vstart + (Vend - Vstart) * t;
    const P = K / Math.pow(V, GAMMA);
    pts.push([V, P]);
  }
  return pts;
}

const LEG_AB = sampleIsothermal(A.V, B.V, K_AB, 60);
const LEG_BC = sampleAdiabatic(B.V, C.V, K_BC, 60);
const LEG_CD = sampleIsothermal(C.V, D.V, K_CD, 60);
const LEG_DA = sampleAdiabatic(D.V, A.V, K_DA, 60);

const polylinePts = (pts: [number, number][]) =>
  pts.map(([V, P]) => `${xOf(V).toFixed(1)},${yOf(P).toFixed(1)}`).join(' ');

// Current state on a leg, given fraction t ∈ [0,1]
function pointOnLeg(t: number, leg: 'AB' | 'BC' | 'CD' | 'DA') {
  if (leg === 'AB') {
    const V = A.V + (B.V - A.V) * t;
    return { V, P: K_AB / V };
  }
  if (leg === 'BC') {
    const V = B.V + (C.V - B.V) * t;
    return { V, P: K_BC / Math.pow(V, GAMMA) };
  }
  if (leg === 'CD') {
    const V = C.V + (D.V - C.V) * t;
    return { V, P: K_CD / V };
  }
  // DA
  const V = D.V + (A.V - D.V) * t;
  return { V, P: K_DA / Math.pow(V, GAMMA) };
}

// ─── Cylinder cartoon (right side of canvas) ────────────────────────────────
// Cylinder occupies its own SVG layered to the right of the PV diagram in JSX.
const CYL_SVG_W = 700;
const CYL_SVG_H = 800;
const CYL_LEFT = 220;
const CYL_RIGHT = 480;
const CYL_BOTTOM = 660;        // gas sits on this y
const CYL_HEIGHT_MAX = 380;    // when V = V_MAX_DRAWN
const V_MIN_DRAWN = 1.5;       // V for the smallest piston state (= A)
const V_MAX_DRAWN = 4.0;       // V for largest (= C)

function gasHeightForV(V: number): number {
  const t = Math.max(0, Math.min(1, (V - V_MIN_DRAWN) / (V_MAX_DRAWN - V_MIN_DRAWN)));
  return 80 + t * (CYL_HEIGHT_MAX - 80);
}

// Reservoir state (what the cylinder is in contact with) per stroke
type Reservoir = 'hot' | 'insulated' | 'cold';
function reservoirAt(frame: number): Reservoir {
  if (frame < T_AXES_END) return 'hot';
  if (frame < T_STROKE1_END) return 'hot';
  if (frame < T_STROKE2_END) return 'insulated';
  if (frame < T_STROKE3_END) return 'cold';
  if (frame < T_STROKE4_END) return 'insulated';
  return 'hot';
}

// Gas colour for a given reservoir + adiabatic mix factor (0=hot, 1=cold)
function gasColor(reservoir: Reservoir, adiabaticMix: number): string {
  if (reservoir === 'hot') return '#ef4444';
  if (reservoir === 'cold') return '#3b82f6';
  // insulated: blend along adiabaticMix
  // mix: 0 → red, 1 → blue
  const r = Math.round(239 + (59 - 239) * adiabaticMix);
  const g = Math.round(68 + (130 - 68) * adiabaticMix);
  const b = Math.round(68 + (246 - 68) * adiabaticMix);
  return `rgb(${r},${g},${b})`;
}

// ─── Component ──────────────────────────────────────────────────────────────
export const CarnotCycleScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Title spring
  const titleScale = spring({ frame, fps, config: PAI_THEME.animation.springDefault });
  const titleOp = interpolate(frame, [0, T_TITLE_END], [0, 1], { extrapolateRight: 'clamp' });
  const axesOp = interpolate(frame, [T_TITLE_END, T_AXES_END], [0, 1], { extrapolateRight: 'clamp' });

  // Determine which leg + fraction t we are currently on
  let activeLeg: 'AB' | 'BC' | 'CD' | 'DA' | 'idle' = 'idle';
  let legT = 0;

  if (frame >= T_AXES_END && frame < T_STROKE1_END) {
    activeLeg = 'AB';
    legT = (frame - T_AXES_END) / STROKE_LEN;
  } else if (frame < T_STROKE2_END) {
    activeLeg = 'BC';
    legT = (frame - T_STROKE1_END) / STROKE_LEN;
  } else if (frame < T_STROKE3_END) {
    activeLeg = 'CD';
    legT = (frame - T_STROKE2_END) / STROKE_LEN;
  } else if (frame < T_STROKE4_END) {
    activeLeg = 'DA';
    legT = (frame - T_STROKE3_END) / STROKE_LEN;
  } else if (frame >= T_STROKE4_END) {
    activeLeg = 'idle';
    legT = 1;
  }

  const tClamped = Math.max(0, Math.min(1, legT));
  const currentState =
    activeLeg === 'idle'
      ? A
      : pointOnLeg(tClamped, activeLeg);

  // Trace progress for each leg (so the curve "draws on" as we move)
  const traceLength = (legId: 'AB' | 'BC' | 'CD' | 'DA') => {
    if (activeLeg === legId) return tClamped;
    // Strokes already completed
    if (legId === 'AB' && frame >= T_STROKE1_END) return 1;
    if (legId === 'BC' && frame >= T_STROKE2_END) return 1;
    if (legId === 'CD' && frame >= T_STROKE3_END) return 1;
    if (legId === 'DA' && frame >= T_STROKE4_END) return 1;
    return 0;
  };

  // Build polyline strings up to the trace progress
  const partialPoly = (pts: [number, number][], frac: number) => {
    if (frac <= 0) return '';
    if (frac >= 1) return polylinePts(pts);
    const cutoff = Math.max(1, Math.floor(pts.length * frac));
    return polylinePts(pts.slice(0, cutoff + 1));
  };

  const traceAB = partialPoly(LEG_AB, traceLength('AB'));
  const traceBC = partialPoly(LEG_BC, traceLength('BC'));
  const traceCD = partialPoly(LEG_CD, traceLength('CD'));
  const traceDA = partialPoly(LEG_DA, traceLength('DA'));

  // Reservoir + colour
  const reservoir = reservoirAt(frame);
  // Adiabatic colour mix: 0 at start of B→C, 1 at end (red→blue)
  // For D→A: 0 at start (cold/blue) → 1 at end (hot/red), so reverse mix.
  let adiabaticMix = 0;
  if (activeLeg === 'BC') adiabaticMix = tClamped;          // hot→cold
  else if (activeLeg === 'DA') adiabaticMix = 1 - tClamped; // cold→hot
  else if (reservoir === 'cold') adiabaticMix = 1;
  else adiabaticMix = 0;

  const fillColor = gasColor(reservoir, adiabaticMix);
  const gasH = gasHeightForV(currentState.V);

  // Stroke labels
  const strokeLabel = (() => {
    switch (activeLeg) {
      case 'AB': return { text: 'Stroke 1 — Isothermal Expansion (T_H) · Q_H absorbed',  color: PAI_THEME.colors.error };
      case 'BC': return { text: 'Stroke 2 — Adiabatic Expansion · cools to T_C',          color: PAI_THEME.colors.warning };
      case 'CD': return { text: 'Stroke 3 — Isothermal Compression (T_C) · Q_C rejected', color: PAI_THEME.colors.info };
      case 'DA': return { text: 'Stroke 4 — Adiabatic Compression · heats to T_H',         color: PAI_THEME.colors.accent };
      default:   return { text: '',  color: PAI_THEME.colors.textMuted };
    }
  })();

  const efficiencyOp = interpolate(frame, [T_STROKE4_END, T_STROKE4_END + 60], [0, 1], { extrapolateRight: 'clamp' });
  const captionOp = interpolate(frame, [T_STROKE4_END + 60, T_STROKE4_END + 120], [0, 1], { extrapolateRight: 'clamp' });

  // ─── Reservoir cartoon (horizontal bar below cylinder) ────────────────────
  const reservoirCol =
    reservoir === 'hot' ? '#ef4444'
    : reservoir === 'cold' ? '#3b82f6'
    : '#7c2d12'; // hatch colour for insulated

  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(135deg, ${PAI_THEME.colors.background}, ${PAI_THEME.colors.backgroundAlt})`,
        flexDirection: 'column', alignItems: 'center', padding: 30,
        fontFamily: PAI_THEME.typography.fontFamily,
      }}
    >
      {/* Title */}
      <h1
        style={{
          fontSize: 56,
          color: PAI_THEME.colors.text,
          margin: '8px 0 4px',
          opacity: titleOp,
          transform: `scale(${titleScale})`,
          textAlign: 'center',
        }}
      >
        The Carnot Cycle — PV Diagram &amp; Piston View
      </h1>
      <p
        style={{
          fontSize: 24,
          color: PAI_THEME.colors.accentLight,
          margin: '0 0 10px',
          fontStyle: 'italic',
          opacity: titleOp,
        }}
      >
        Two reversible isotherms (T_H, T_C) joined by two reversible adiabats — the most efficient possible cycle.
      </p>

      {/* Stroke banner */}
      <div
        style={{
          height: 36,
          color: strokeLabel.color,
          fontSize: 24,
          fontWeight: 700,
          opacity: strokeLabel.text ? 1 : 0,
          marginBottom: 4,
        }}
      >
        {strokeLabel.text}
      </div>

      {/* Side-by-side layout: PV diagram (left) and piston (right) */}
      <div style={{ display: 'flex', flexDirection: 'row', alignItems: 'flex-start', gap: 40 }}>
        {/* ────── PV DIAGRAM ────── */}
        <svg width={PLOT_W} height={PLOT_H}>
          <defs>
            <marker id="cc-arr-r" markerWidth={12} markerHeight={12} refX={11} refY={6} orient="auto">
              <polygon points="0,0 12,6 0,12" fill={PAI_THEME.colors.error} />
            </marker>
            <marker id="cc-arr-o" markerWidth={12} markerHeight={12} refX={11} refY={6} orient="auto">
              <polygon points="0,0 12,6 0,12" fill={PAI_THEME.colors.warning} />
            </marker>
            <marker id="cc-arr-b" markerWidth={12} markerHeight={12} refX={11} refY={6} orient="auto">
              <polygon points="0,0 12,6 0,12" fill={PAI_THEME.colors.info} />
            </marker>
            <marker id="cc-arr-p" markerWidth={12} markerHeight={12} refX={11} refY={6} orient="auto">
              <polygon points="0,0 12,6 0,12" fill={PAI_THEME.colors.accent} />
            </marker>
          </defs>

          {/* Plot panel */}
          <rect
            x={PLOT_LEFT}
            y={PLOT_TOP}
            width={PLOT_RIGHT - PLOT_LEFT}
            height={PLOT_BOTTOM - PLOT_TOP}
            fill="rgba(255,255,255,0.04)"
            stroke={PAI_THEME.colors.textMuted}
            opacity={axesOp}
          />

          {/* Grid */}
          <g opacity={axesOp * 0.4}>
            {[2, 3, 4].map((v) => (
              <line key={`gv-${v}`} x1={xOf(v)} y1={PLOT_TOP} x2={xOf(v)} y2={PLOT_BOTTOM}
                stroke={PAI_THEME.colors.textDark} strokeWidth={1} />
            ))}
            {[2, 3, 4].map((p) => (
              <line key={`gp-${p}`} x1={PLOT_LEFT} y1={yOf(p)} x2={PLOT_RIGHT} y2={yOf(p)}
                stroke={PAI_THEME.colors.textDark} strokeWidth={1} />
            ))}
          </g>

          {/* Axes */}
          <line x1={PLOT_LEFT} y1={PLOT_BOTTOM} x2={PLOT_RIGHT} y2={PLOT_BOTTOM}
            stroke={PAI_THEME.colors.text} strokeWidth={3} opacity={axesOp} />
          <line x1={PLOT_LEFT} y1={PLOT_TOP} x2={PLOT_LEFT} y2={PLOT_BOTTOM}
            stroke={PAI_THEME.colors.text} strokeWidth={3} opacity={axesOp} />

          <text x={(PLOT_LEFT + PLOT_RIGHT) / 2} y={PLOT_BOTTOM + 50}
            textAnchor="middle" fill={PAI_THEME.colors.text} fontSize={28} fontWeight={700}
            opacity={axesOp}>Volume V</text>
          <text x={PLOT_LEFT - 60} y={(PLOT_TOP + PLOT_BOTTOM) / 2}
            textAnchor="middle" fill={PAI_THEME.colors.text} fontSize={28} fontWeight={700}
            transform={`rotate(-90 ${PLOT_LEFT - 60} ${(PLOT_TOP + PLOT_BOTTOM) / 2})`}
            opacity={axesOp}>Pressure P</text>

          {/* Faint full cycle outline for orientation (drawn once axes are in) */}
          <g opacity={axesOp * 0.2}>
            <polyline points={polylinePts(LEG_AB)} fill="none" stroke={PAI_THEME.colors.error}   strokeWidth={3} />
            <polyline points={polylinePts(LEG_BC)} fill="none" stroke={PAI_THEME.colors.warning} strokeWidth={3} strokeDasharray="8 6" />
            <polyline points={polylinePts(LEG_CD)} fill="none" stroke={PAI_THEME.colors.info}    strokeWidth={3} />
            <polyline points={polylinePts(LEG_DA)} fill="none" stroke={PAI_THEME.colors.accent}  strokeWidth={3} strokeDasharray="8 6" />
          </g>

          {/* "Live" trace — drawn as we walk the cycle */}
          {traceAB && (
            <polyline points={traceAB} fill="none" stroke={PAI_THEME.colors.error} strokeWidth={6} strokeLinecap="round" />
          )}
          {traceBC && (
            <polyline points={traceBC} fill="none" stroke={PAI_THEME.colors.warning} strokeWidth={6} strokeLinecap="round" strokeDasharray="14 8" />
          )}
          {traceCD && (
            <polyline points={traceCD} fill="none" stroke={PAI_THEME.colors.info} strokeWidth={6} strokeLinecap="round" />
          )}
          {traceDA && (
            <polyline points={traceDA} fill="none" stroke={PAI_THEME.colors.accent} strokeWidth={6} strokeLinecap="round" strokeDasharray="14 8" />
          )}

          {/* State dots */}
          <g opacity={axesOp}>
            {[
              { S: A, label: 'A', fill: PAI_THEME.colors.error },
              { S: B, label: 'B', fill: PAI_THEME.colors.warning },
              { S: C, label: 'C', fill: PAI_THEME.colors.info },
              { S: D, label: 'D', fill: PAI_THEME.colors.accent },
            ].map((s) => (
              <g key={s.label}>
                <circle cx={xOf(s.S.V)} cy={yOf(s.S.P)} r={10} fill={s.fill} stroke={PAI_THEME.colors.text} strokeWidth={2} />
                <text x={xOf(s.S.V) + 18} y={yOf(s.S.P) + 8} fill={PAI_THEME.colors.text} fontSize={28} fontWeight={700}>
                  {s.label}
                </text>
              </g>
            ))}
          </g>

          {/* Moving "current state" pointer */}
          {activeLeg !== 'idle' && (
            <g>
              <circle
                cx={xOf(currentState.V)}
                cy={yOf(currentState.P)}
                r={16}
                fill="#fde68a"
                stroke={PAI_THEME.colors.text}
                strokeWidth={3}
              />
              <circle
                cx={xOf(currentState.V)}
                cy={yOf(currentState.P)}
                r={6}
                fill={PAI_THEME.colors.text}
              />
            </g>
          )}

          {/* Legend (bottom-right of plot) */}
          <g transform={`translate(${PLOT_LEFT + 20}, ${PLOT_TOP + 20})`} opacity={axesOp}>
            <rect width={310} height={120} fill="rgba(15,23,42,0.6)" stroke={PAI_THEME.colors.textMuted} rx={8} />
            <line x1={14} y1={28} x2={50} y2={28} stroke={PAI_THEME.colors.error} strokeWidth={5} />
            <text x={60} y={34} fill={PAI_THEME.colors.text} fontSize={18}>isothermal (PV = const)</text>
            <line x1={14} y1={58} x2={50} y2={58} stroke={PAI_THEME.colors.warning} strokeWidth={5} strokeDasharray="6 4" />
            <text x={60} y={64} fill={PAI_THEME.colors.text} fontSize={18}>adiabatic (PV^γ = const)</text>
            <text x={14} y={94} fill={PAI_THEME.colors.textMuted} fontSize={14}>γ = 1.4  ·  enclosed area = W_net</text>
          </g>
        </svg>

        {/* ────── PISTON / CYLINDER ────── */}
        <svg width={CYL_SVG_W} height={CYL_SVG_H}>
          <defs>
            <pattern id="cc-insul-pat" x={0} y={0} width={10} height={10} patternUnits="userSpaceOnUse">
              <path d="M 0 10 L 10 0" stroke="#7c2d12" strokeWidth={2} />
            </pattern>
          </defs>

          {/* Header */}
          <text x={CYL_SVG_W / 2} y={50} textAnchor="middle"
            fill={PAI_THEME.colors.text} fontSize={28} fontWeight={700} opacity={axesOp}>
            Working substance (gas in cylinder)
          </text>

          {/* Cylinder walls */}
          <line x1={CYL_LEFT}  y1={120} x2={CYL_LEFT}  y2={CYL_BOTTOM} stroke={PAI_THEME.colors.text} strokeWidth={5} opacity={axesOp} />
          <line x1={CYL_RIGHT} y1={120} x2={CYL_RIGHT} y2={CYL_BOTTOM} stroke={PAI_THEME.colors.text} strokeWidth={5} opacity={axesOp} />
          <line x1={CYL_LEFT}  y1={CYL_BOTTOM} x2={CYL_RIGHT} y2={CYL_BOTTOM} stroke={PAI_THEME.colors.text} strokeWidth={5} opacity={axesOp} />

          {/* Gas (height proportional to V) */}
          <rect
            x={CYL_LEFT + 6}
            y={CYL_BOTTOM - gasH}
            width={CYL_RIGHT - CYL_LEFT - 12}
            height={gasH}
            fill={fillColor}
            opacity={0.7}
          />

          {/* Piston */}
          <rect
            x={CYL_LEFT - 8}
            y={CYL_BOTTOM - gasH - 22}
            width={CYL_RIGHT - CYL_LEFT + 16}
            height={22}
            fill="#475569"
            stroke={PAI_THEME.colors.text}
            strokeWidth={3}
          />
          {/* Piston rod */}
          <line
            x1={(CYL_LEFT + CYL_RIGHT) / 2}
            y1={CYL_BOTTOM - gasH - 22}
            x2={(CYL_LEFT + CYL_RIGHT) / 2}
            y2={70}
            stroke={PAI_THEME.colors.text}
            strokeWidth={6}
          />
          <rect
            x={(CYL_LEFT + CYL_RIGHT) / 2 - 50}
            y={50}
            width={100}
            height={22}
            fill="#475569"
            stroke={PAI_THEME.colors.text}
            strokeWidth={3}
          />

          {/* Reservoir / insulator slab below cylinder */}
          {reservoir === 'insulated' ? (
            <rect x={CYL_LEFT - 30} y={CYL_BOTTOM + 10} width={CYL_RIGHT - CYL_LEFT + 60} height={28}
              fill="url(#cc-insul-pat)" stroke="#7c2d12" strokeWidth={2} />
          ) : (
            <rect x={CYL_LEFT - 30} y={CYL_BOTTOM + 10} width={CYL_RIGHT - CYL_LEFT + 60} height={28}
              fill={reservoirCol} opacity={0.7} stroke={reservoirCol} strokeWidth={2} />
          )}

          {/* Reservoir label */}
          <text x={(CYL_LEFT + CYL_RIGHT) / 2} y={CYL_BOTTOM + 64}
            textAnchor="middle"
            fill={
              reservoir === 'hot' ? PAI_THEME.colors.error
              : reservoir === 'cold' ? PAI_THEME.colors.info
              : '#7c2d12'
            }
            fontSize={26} fontWeight={700}>
            {reservoir === 'hot'        && 'Hot reservoir (T_H)'}
            {reservoir === 'cold'       && 'Cold reservoir (T_C)'}
            {reservoir === 'insulated'  && 'Insulated (Q = 0)'}
          </text>

          {/* Heat-flow arrow when in contact with reservoir */}
          {(reservoir === 'hot' || reservoir === 'cold') && activeLeg !== 'idle' && (
            <>
              {(() => {
                // Hot: heat flows up into gas (Q_H in).  Cold: heat flows down into reservoir (Q_C out).
                const isHot = reservoir === 'hot';
                const x = (CYL_LEFT + CYL_RIGHT) / 2 - 80;
                const y1 = isHot ? CYL_BOTTOM + 20 : CYL_BOTTOM - 20;
                const y2 = isHot ? CYL_BOTTOM - 20 : CYL_BOTTOM + 20;
                const col = isHot ? PAI_THEME.colors.error : PAI_THEME.colors.info;
                const label = isHot ? 'Q_H' : 'Q_C';
                return (
                  <>
                    <line
                      x1={x} y1={y1} x2={x} y2={y2}
                      stroke={col} strokeWidth={6}
                      markerEnd={isHot ? 'url(#cc-arr-r)' : 'url(#cc-arr-b)'}
                    />
                    <text x={x - 56} y={(y1 + y2) / 2 + 8} fill={col} fontSize={26} fontWeight={700}>
                      {label}
                    </text>
                  </>
                );
              })()}
            </>
          )}

          {/* State variable readout */}
          <g opacity={axesOp}>
            <rect x={CYL_SVG_W - 240} y={120} width={220} height={120}
              fill="rgba(15,23,42,0.6)" stroke={PAI_THEME.colors.textMuted} rx={8} />
            <text x={CYL_SVG_W - 230} y={150} fill={PAI_THEME.colors.textMuted} fontSize={18}>state</text>
            <text x={CYL_SVG_W - 230} y={182} fill={PAI_THEME.colors.text} fontSize={26} fontWeight={700}>
              V = {currentState.V.toFixed(2)}
            </text>
            <text x={CYL_SVG_W - 230} y={216} fill={PAI_THEME.colors.text} fontSize={26} fontWeight={700}>
              P = {currentState.P.toFixed(2)}
            </text>
          </g>
        </svg>
      </div>

      {/* Efficiency formula reveal */}
      <div
        style={{
          marginTop: 8,
          opacity: efficiencyOp,
          color: PAI_THEME.colors.text,
          fontSize: 30,
          textAlign: 'center',
          maxWidth: 1700,
        }}
      >
        Carnot efficiency:&nbsp;&nbsp;
        <span style={{ color: PAI_THEME.colors.success, fontWeight: 700 }}>
          η_Carnot = 1 − T_C ⁄ T_H
        </span>
        &nbsp;&nbsp;<span style={{ color: PAI_THEME.colors.textMuted }}>(temperatures in Kelvin)</span>
      </div>

      <div
        style={{
          marginTop: 14,
          color: PAI_THEME.colors.textMuted,
          fontSize: 22,
          opacity: captionOp,
          textAlign: 'center',
          maxWidth: 1700,
          fontStyle: 'italic',
        }}
      >
        No real engine operating between the same two temperatures can do better — the cycle has to be reversible to attain the bound.
      </div>
    </AbsoluteFill>
  );
};
