/**
 * CardiacCycleScene — Animated cardiac cycle.
 *
 * Frames @ 30 fps (28 s total = 840 frames):
 *   0–60      Title fades in
 *   60–780    Heart beats — 10 cycles, 72 frames each (~2.4 s/beat for clarity)
 *               Each beat traces five phases of the cardiac cycle:
 *                 Atrial systole          — atria contract, AV valves open
 *                 Isovolumetric contract  — all valves shut, pressure climbs
 *                 Ventricular ejection    — semilunar valves open, blood out
 *                 Isovolumetric relaxation— all valves shut, pressure falls
 *                 Ventricular filling     — AV valves open, passive fill
 *   780–840   Closing caption fades in
 *
 * Visual structure (1920 × 1080):
 *   - Left (≈ x 80–960): heart cross-section (4 chambers + 4 valves) with
 *                       animated chamber-wall thickness, valve states, and
 *                       directional blood flow arrows
 *   - Right (≈ x 980–1880): live pressure traces — aortic, ventricular,
 *                          atrial — scrolling out as the cycle runs, plus a
 *                          P-V loop building beat by beat
 *   - Top: title strip with phase caption (changes per phase)
 *   - Bottom: phase narration strip
 *
 * Remotion gotcha applied throughout: interpolate(value, [a, b], [c, d])
 * requires a < b. To get decreasing output as input grows, swap c and d.
 */
import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate, spring, useVideoConfig } from 'remotion';
import { PAI_THEME } from '../theme';

// ── Top-level timing ─────────────────────────────────────────────────────────
const FPS = 30;
const F_TITLE_END   = 60;
const F_BEAT_START  = 60;
const BEAT_FRAMES   = 72;       // 2.4 s per beat — slowed for legibility
const N_BEATS       = 10;
const F_BEAT_END    = F_BEAT_START + BEAT_FRAMES * N_BEATS;   // 780
const F_CLOSE_END   = 840;

// Phase windows inside one beat (0..BEAT_FRAMES)
//   atrial systole          0  →  9   (~0.30 s)
//   isovolumetric contract  9  → 16   (~0.23 s)
//   ventricular ejection   16  → 36   (~0.67 s)
//   isovolumetric relax    36  → 45   (~0.30 s)
//   ventricular filling    45  → 72   (~0.90 s)
const PH_AS_END  = 9;
const PH_IC_END  = 16;
const PH_VE_END  = 36;
const PH_IR_END  = 45;
const PH_VF_END  = BEAT_FRAMES;   // = 72

type Phase = 'AS' | 'IC' | 'VE' | 'IR' | 'VF';

const PHASE_INFO: Record<Phase, { label: string; narration: string; color: string }> = {
  AS: { label: 'Atrial Systole',           narration: 'Atria contract — blood pushed into ventricles',     color: PAI_THEME.colors.atrialSystole },
  IC: { label: 'Isovolumetric Contraction',narration: 'All four valves closed — ventricular pressure climbs', color: PAI_THEME.colors.isovolumetricContraction },
  VE: { label: 'Ventricular Ejection',     narration: 'Semilunar valves open — blood ejected to arteries', color: PAI_THEME.colors.ventricularEjection },
  IR: { label: 'Isovolumetric Relaxation', narration: 'All four valves closed — pressure falls in ventricles', color: PAI_THEME.colors.isovolumetricRelaxation },
  VF: { label: 'Ventricular Filling',      narration: 'AV valves open — ventricles fill passively',        color: PAI_THEME.colors.ventricularFilling },
};

const getBeatLocal = (frame: number): { local: number; beatIdx: number } => {
  if (frame < F_BEAT_START) return { local: 0, beatIdx: 0 };
  if (frame >= F_BEAT_END)  return { local: BEAT_FRAMES - 1, beatIdx: N_BEATS - 1 };
  const since = frame - F_BEAT_START;
  return { local: since % BEAT_FRAMES, beatIdx: Math.floor(since / BEAT_FRAMES) };
};

const getPhase = (local: number): Phase => {
  if (local < PH_AS_END) return 'AS';
  if (local < PH_IC_END) return 'IC';
  if (local < PH_VE_END) return 'VE';
  if (local < PH_IR_END) return 'IR';
  return 'VF';
};

// ── Layout ───────────────────────────────────────────────────────────────────
const W = 1920;
const H = 1080;

// Heart panel (left)
const HEART_CX = 540;
const HEART_CY = 580;

// Pressure-trace panel (right)
const TRACE_X0 = 1000;
const TRACE_X1 = 1880;
const TRACE_Y_TOP = 230;
const TRACE_Y_BOTTOM = 580;
// Pressure range 0..130 mmHg
const PRESSURE_MAX = 130;

// P-V loop panel (below the trace)
const PV_X0 = 1000;
const PV_X1 = 1450;
const PV_Y_TOP = 700;
const PV_Y_BOTTOM = 1000;
// PV ranges: volume 40..140 mL, pressure 0..130 mmHg

// ── Beat-physiology functions ────────────────────────────────────────────────
/**
 * Left-ventricular pressure (mmHg) as a function of position-in-beat (0..72).
 * Hand-shaped piecewise curve approximating the Wiggers diagram.
 */
const ventricularPressure = (local: number): number => {
  // Atrial systole: LV pressure ~5-8 mmHg
  if (local < PH_AS_END) {
    return interpolate(local, [0, PH_AS_END], [5, 10], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  }
  // Isovolumetric contraction: 10 → 80 mmHg
  if (local < PH_IC_END) {
    return interpolate(local, [PH_AS_END, PH_IC_END], [10, 80], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  }
  // Ventricular ejection: 80 → ~120 (peak around mid-ejection) → 95
  if (local < PH_VE_END) {
    // bell-shaped — split into rise and fall halves
    const mid = (PH_IC_END + PH_VE_END) / 2;
    if (local < mid) {
      return interpolate(local, [PH_IC_END, mid], [80, 120], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
    }
    return interpolate(local, [mid, PH_VE_END], [120, 95], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  }
  // Isovolumetric relaxation: 95 → ~5
  if (local < PH_IR_END) {
    return interpolate(local, [PH_VE_END, PH_IR_END], [95, 5], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  }
  // Ventricular filling: 5 → 4
  return interpolate(local, [PH_IR_END, PH_VF_END], [5, 4], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
};

const aorticPressure = (local: number): number => {
  // Diastolic baseline ~80; during ejection rises to ~120 with dicrotic notch
  if (local < PH_IC_END) {
    // Falling slowly from ~85 to ~80 during atrial systole + IC
    return interpolate(local, [0, PH_IC_END], [85, 80], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  }
  if (local < PH_VE_END) {
    // Tracks LV during ejection, peaks at 120
    const mid = (PH_IC_END + PH_VE_END) / 2;
    if (local < mid) {
      return interpolate(local, [PH_IC_END, mid], [80, 120], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
    }
    return interpolate(local, [mid, PH_VE_END], [120, 95], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  }
  if (local < PH_IR_END) {
    // Dicrotic notch then resumes decay
    if (local < PH_VE_END + 2) {
      return interpolate(local, [PH_VE_END, PH_VE_END + 2], [95, 90], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
    }
    return interpolate(local, [PH_VE_END + 2, PH_IR_END], [90, 85], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  }
  // Filling — slow exponential-ish decay 85 → 80
  return interpolate(local, [PH_IR_END, PH_VF_END], [85, 80], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
};

const atrialPressure = (local: number): number => {
  // a-wave during atrial systole, c-wave at IC, x descent during ejection,
  // v-wave at end-ejection, y descent during filling
  if (local < PH_AS_END) {
    // a-wave: rises 6 → 12 → 8
    if (local < PH_AS_END / 2) {
      return interpolate(local, [0, PH_AS_END / 2], [6, 12], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
    }
    return interpolate(local, [PH_AS_END / 2, PH_AS_END], [12, 8], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  }
  if (local < PH_IC_END) {
    // c-wave: small bump 8 → 10 → 6
    return interpolate(local, [PH_AS_END, PH_IC_END], [8, 6], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  }
  if (local < PH_VE_END) {
    // x descent then v-wave: 6 → 4 → 10
    const mid = (PH_IC_END + PH_VE_END) / 2;
    if (local < mid) {
      return interpolate(local, [PH_IC_END, mid], [6, 4], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
    }
    return interpolate(local, [mid, PH_VE_END], [4, 10], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  }
  if (local < PH_IR_END) {
    // v-wave peak then y-descent start: 10 → 8
    return interpolate(local, [PH_VE_END, PH_IR_END], [10, 8], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  }
  // Filling: y descent 8 → 5
  return interpolate(local, [PH_IR_END, PH_VF_END], [8, 5], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
};

/**
 * Left-ventricular volume (mL) over one beat — 50 (ESV) → 120 (EDV) → 50.
 */
const ventricularVolume = (local: number): number => {
  // Atrial systole: 110 → 120
  if (local < PH_AS_END) {
    return interpolate(local, [0, PH_AS_END], [110, 120], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  }
  // IC: 120 (isovolumetric — no change)
  if (local < PH_IC_END) {
    return 120;
  }
  // VE: 120 → 50
  if (local < PH_VE_END) {
    return interpolate(local, [PH_IC_END, PH_VE_END], [120, 50], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  }
  // IR: 50 (isovolumetric)
  if (local < PH_IR_END) {
    return 50;
  }
  // VF: 50 → 110
  return interpolate(local, [PH_IR_END, PH_VF_END], [50, 110], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
};

// ── Heart-anatomy helpers ────────────────────────────────────────────────────
const ChamberPath: React.FC<{
  cx: number; cy: number; rx: number; ry: number;
  fill: string; stroke: string; strokeWidth: number;
  opacity?: number;
}> = ({ cx, cy, rx, ry, fill, stroke, strokeWidth, opacity = 1 }) => (
  <ellipse cx={cx} cy={cy} rx={rx} ry={ry} fill={fill} stroke={stroke} strokeWidth={strokeWidth} opacity={opacity}/>
);

/** Render an AV (mitral/tricuspid) or semilunar (aortic/pulmonary) valve.
 *  When open=true, the two leaflets swing apart; when closed, they meet.
 */
const Valve: React.FC<{
  x: number; y: number; w: number;
  open: boolean;
  vertical?: boolean;
  color: string;
}> = ({ x, y, w, open, vertical = false, color }) => {
  const span = w * 0.45;
  const tilt = open ? 0.5 : 0.0;
  if (vertical) {
    // Vertical valve (leaflets swing left/right) — for semilunar valves at top of ventricle
    const lx = x - span * tilt;
    const rx = x + span * tilt;
    return (
      <g>
        <line x1={x - w/2} y1={y - 4} x2={lx} y2={y + span * 0.8} stroke={color} strokeWidth={4} strokeLinecap="round"/>
        <line x1={x + w/2} y1={y - 4} x2={rx} y2={y + span * 0.8} stroke={color} strokeWidth={4} strokeLinecap="round"/>
      </g>
    );
  }
  // Horizontal valve (leaflets swing up/down) — AV valves between atria and ventricles
  const upY = y - span * tilt;
  return (
    <g>
      <line x1={x - w/2} y1={y - 2} x2={x - 4} y2={upY} stroke={color} strokeWidth={4} strokeLinecap="round"/>
      <line x1={x + w/2} y1={y - 2} x2={x + 4} y2={upY} stroke={color} strokeWidth={4} strokeLinecap="round"/>
    </g>
  );
};

/** Render a directional flow arrow (dashed) for blood movement. */
const FlowArrow: React.FC<{
  x1: number; y1: number; x2: number; y2: number;
  color: string; visible: boolean;
}> = ({ x1, y1, x2, y2, color, visible }) => {
  if (!visible) return null;
  const dx = x2 - x1, dy = y2 - y1;
  const len = Math.hypot(dx, dy) || 1;
  const ux = dx / len, uy = dy / len;
  const px = -uy, py = ux;       // perpendicular for arrow head
  const ah = 14;
  const aw = 7;
  const tipX = x2, tipY = y2;
  const baseX = x2 - ux * ah, baseY = y2 - uy * ah;
  const leftX = baseX + px * aw, leftY = baseY + py * aw;
  const rightX = baseX - px * aw, rightY = baseY - py * aw;
  return (
    <g opacity={0.9}>
      <line x1={x1} y1={y1} x2={x2} y2={y2} stroke={color} strokeWidth={5} strokeLinecap="round" strokeDasharray="10 8"/>
      <polygon points={`${tipX},${tipY} ${leftX},${leftY} ${rightX},${rightY}`} fill={color}/>
    </g>
  );
};

// ── HeartCrossSection — the animated anatomy ─────────────────────────────────
const HeartCrossSection: React.FC<{ local: number; phase: Phase }> = ({ local, phase }) => {
  // Chamber geometry — base sizes
  // Atria sit at top, ventricles at bottom.
  // Right atrium (left side as you face the patient) cx, Right ventricle below.
  const RA_CX = HEART_CX - 110;
  const RA_CY = HEART_CY - 140;
  const LA_CX = HEART_CX + 110;
  const LA_CY = HEART_CY - 140;
  const RV_CX = HEART_CX - 110;
  const RV_CY = HEART_CY + 60;
  const LV_CX = HEART_CX + 110;
  const LV_CY = HEART_CY + 60;

  // Atrial contraction in AS phase: atria shrink ~12% during AS
  const atrialShrink = (() => {
    if (phase === 'AS') {
      const t = interpolate(local, [0, PH_AS_END], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
      // Out range swapped: bigger atrium → smaller atrium as t grows
      return interpolate(t, [0, 1], [1.0, 0.86], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
    }
    // Atria refilling smoothly during the rest of the cycle, snapping back early in VF
    if (phase === 'VF') {
      return interpolate(local, [PH_IR_END, PH_VF_END], [0.86, 1.0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
    }
    return 0.86 + 0.05;   // intermediate during IC/VE/IR — atria gradually re-filling
  })();

  // Ventricular volume drives ventricular radius: V from 50..120 mL → radius scale 0.7..1.0
  const lvVol = ventricularVolume(local);
  const ventScale = interpolate(lvVol, [50, 120], [0.72, 1.05], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  // Ventricular wall thickening during systole (IC + VE): walls visually thicker
  const wallThick = (() => {
    if (phase === 'IC' || phase === 'VE') {
      const t = phase === 'IC'
        ? interpolate(local, [PH_AS_END, PH_IC_END], [0, 0.6], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' })
        : interpolate(local, [PH_IC_END, PH_VE_END], [0.6, 1.0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
      return 8 + 6 * t;
    }
    return 7;
  })();

  // Valve states per phase:
  //   AS  — AV valves OPEN (atria pushing into ventricles), semilunars CLOSED
  //   IC  — all closed
  //   VE  — AV closed, semilunars OPEN
  //   IR  — all closed
  //   VF  — AV OPEN (passive filling), semilunars CLOSED
  const avOpen = phase === 'AS' || phase === 'VF';
  const slOpen = phase === 'VE';

  // Flow arrows visibility per phase
  const showAtriumToVentricle = phase === 'AS' || phase === 'VF';
  const showVentricleToArtery = phase === 'VE';

  // Atrial radii (compressed during atrial systole)
  const atriumRX = 80 * atrialShrink;
  const atriumRY = 56 * atrialShrink;

  // Ventricular radii (scaled by volume)
  const ventRX = 110 * ventScale;
  const ventRY = 100 * ventScale;

  return (
    <g>
      {/* ── Heart outline / cardiac silhouette (faint) ─────────── */}
      <path
        d={`M ${HEART_CX - 220} ${HEART_CY - 200}
            Q ${HEART_CX - 270} ${HEART_CY - 60} ${HEART_CX - 200} ${HEART_CY + 80}
            Q ${HEART_CX - 130} ${HEART_CY + 220} ${HEART_CX + 0} ${HEART_CY + 240}
            Q ${HEART_CX + 130} ${HEART_CY + 220} ${HEART_CX + 200} ${HEART_CY + 80}
            Q ${HEART_CX + 270} ${HEART_CY - 60} ${HEART_CX + 220} ${HEART_CY - 200}
            Q ${HEART_CX + 100} ${HEART_CY - 250} ${HEART_CX + 0} ${HEART_CY - 230}
            Q ${HEART_CX - 100} ${HEART_CY - 250} ${HEART_CX - 220} ${HEART_CY - 200} Z`}
        fill={PAI_THEME.colors.coolWash}
        stroke={PAI_THEME.colors.textMuted}
        strokeWidth={2.5}
        opacity={0.5}
      />

      {/* ── Vena cavae (deoxygenated, entering RA) ─────────────── */}
      <line
        x1={RA_CX - 60} y1={RA_CY - 140}
        x2={RA_CX - 12} y2={RA_CY - atriumRY}
        stroke={PAI_THEME.colors.deoxygenated}
        strokeWidth={20} strokeLinecap="round"
      />
      <text x={RA_CX - 70} y={RA_CY - 156} fontSize={18} fill={PAI_THEME.colors.text} textAnchor="end" fontWeight={700}>
        vena cavae
      </text>

      {/* ── Pulmonary veins (oxygenated, entering LA) ──────────── */}
      <line
        x1={LA_CX + 60} y1={LA_CY - 140}
        x2={LA_CX + 12} y2={LA_CY - atriumRY}
        stroke={PAI_THEME.colors.oxygenated}
        strokeWidth={20} strokeLinecap="round"
      />
      <text x={LA_CX + 70} y={LA_CY - 156} fontSize={18} fill={PAI_THEME.colors.text} textAnchor="start" fontWeight={700}>
        pulmonary veins
      </text>

      {/* ── Right atrium ───────────────────────────────────────── */}
      <ChamberPath
        cx={RA_CX} cy={RA_CY} rx={atriumRX} ry={atriumRY}
        fill="rgba(30, 58, 138, 0.20)"
        stroke={PAI_THEME.colors.deoxygenated}
        strokeWidth={4}
      />
      <text x={RA_CX} y={RA_CY + 6} fontSize={22} fill={PAI_THEME.colors.text} textAnchor="middle" fontWeight={700}>RA</text>

      {/* ── Left atrium ────────────────────────────────────────── */}
      <ChamberPath
        cx={LA_CX} cy={LA_CY} rx={atriumRX} ry={atriumRY}
        fill="rgba(220, 38, 38, 0.18)"
        stroke={PAI_THEME.colors.oxygenated}
        strokeWidth={4}
      />
      <text x={LA_CX} y={LA_CY + 6} fontSize={22} fill={PAI_THEME.colors.text} textAnchor="middle" fontWeight={700}>LA</text>

      {/* ── Septum (interventricular wall) ─────────────────────── */}
      <line
        x1={HEART_CX} y1={HEART_CY - 40}
        x2={HEART_CX} y2={HEART_CY + 200}
        stroke={PAI_THEME.colors.chamberWall}
        strokeWidth={6}
      />

      {/* ── Right ventricle ────────────────────────────────────── */}
      <ChamberPath
        cx={RV_CX} cy={RV_CY} rx={ventRX} ry={ventRY}
        fill="rgba(30, 58, 138, 0.30)"
        stroke={PAI_THEME.colors.deoxygenated}
        strokeWidth={wallThick}
      />
      <text x={RV_CX} y={RV_CY + 8} fontSize={28} fill={PAI_THEME.colors.text} textAnchor="middle" fontWeight={700}>RV</text>

      {/* ── Left ventricle (thicker wall — main pump) ──────────── */}
      <ChamberPath
        cx={LV_CX} cy={LV_CY} rx={ventRX} ry={ventRY}
        fill="rgba(220, 38, 38, 0.28)"
        stroke={PAI_THEME.colors.oxygenated}
        strokeWidth={wallThick + 4}
      />
      <text x={LV_CX} y={LV_CY + 8} fontSize={28} fill={PAI_THEME.colors.text} textAnchor="middle" fontWeight={700}>LV</text>

      {/* ── AV valves ──────────────────────────────────────────── */}
      {/* Tricuspid valve (RA → RV) */}
      <Valve x={RA_CX} y={RA_CY + atriumRY + 6} w={70} open={avOpen} color={avOpen ? PAI_THEME.colors.valveOpen : PAI_THEME.colors.valveClosed}/>
      <text x={RA_CX - 90} y={RA_CY + atriumRY + 30} fontSize={14} fill={PAI_THEME.colors.textMuted} fontWeight={700}>tricuspid</text>

      {/* Mitral valve (LA → LV) */}
      <Valve x={LA_CX} y={LA_CY + atriumRY + 6} w={70} open={avOpen} color={avOpen ? PAI_THEME.colors.valveOpen : PAI_THEME.colors.valveClosed}/>
      <text x={LA_CX + 90} y={LA_CY + atriumRY + 30} fontSize={14} fill={PAI_THEME.colors.textMuted} fontWeight={700}>mitral</text>

      {/* ── Semilunar valves + outflow tracts ──────────────────── */}
      {/* Pulmonary artery (from RV, going up-left) */}
      <line
        x1={RV_CX - 30} y1={RV_CY - ventRY - 4}
        x2={RV_CX - 60} y2={RV_CY - ventRY - 80}
        stroke={PAI_THEME.colors.pulmonaryArtery}
        strokeWidth={22} strokeLinecap="round"
      />
      <Valve x={RV_CX - 30} y={RV_CY - ventRY + 4} w={56} open={slOpen} vertical color={slOpen ? PAI_THEME.colors.valveOpen : PAI_THEME.colors.valveClosed}/>
      <text x={RV_CX - 78} y={RV_CY - ventRY - 96} fontSize={16} fill={PAI_THEME.colors.text} textAnchor="end" fontWeight={700}>
        pulmonary
      </text>
      <text x={RV_CX - 78} y={RV_CY - ventRY - 78} fontSize={16} fill={PAI_THEME.colors.text} textAnchor="end" fontWeight={700}>
        artery
      </text>

      {/* Aorta (from LV, going up-right then arching) */}
      <path
        d={`M ${LV_CX + 30} ${LV_CY - ventRY - 4}
            L ${LV_CX + 60} ${LV_CY - ventRY - 80}
            Q ${LV_CX + 40} ${LV_CY - ventRY - 130} ${LV_CX + 0} ${LV_CY - ventRY - 150}`}
        fill="none"
        stroke={PAI_THEME.colors.aorta}
        strokeWidth={22} strokeLinecap="round"
      />
      <Valve x={LV_CX + 30} y={LV_CY - ventRY + 4} w={56} open={slOpen} vertical color={slOpen ? PAI_THEME.colors.valveOpen : PAI_THEME.colors.valveClosed}/>
      <text x={LV_CX + 90} y={LV_CY - ventRY - 110} fontSize={16} fill={PAI_THEME.colors.text} textAnchor="start" fontWeight={700}>
        aorta
      </text>

      {/* ── Flow arrows ────────────────────────────────────────── */}
      {/* Atrium → ventricle during AV-valve-open phases */}
      <FlowArrow
        x1={RA_CX} y1={RA_CY + atriumRY + 18}
        x2={RV_CX} y2={RV_CY - ventRY + 18}
        color={PAI_THEME.colors.deoxygenated}
        visible={showAtriumToVentricle}
      />
      <FlowArrow
        x1={LA_CX} y1={LA_CY + atriumRY + 18}
        x2={LV_CX} y2={LV_CY - ventRY + 18}
        color={PAI_THEME.colors.oxygenated}
        visible={showAtriumToVentricle}
      />

      {/* Ventricle → artery during ejection */}
      <FlowArrow
        x1={RV_CX - 30} y1={RV_CY - ventRY + 12}
        x2={RV_CX - 60} y2={RV_CY - ventRY - 70}
        color={PAI_THEME.colors.pulmonaryArtery}
        visible={showVentricleToArtery}
      />
      <FlowArrow
        x1={LV_CX + 30} y1={LV_CY - ventRY + 12}
        x2={LV_CX + 60} y2={LV_CY - ventRY - 70}
        color={PAI_THEME.colors.aorta}
        visible={showVentricleToArtery}
      />

      {/* ── Phase legend (lower-left of heart) ──────────────────── */}
      <g transform={`translate(${HEART_CX - 240}, ${HEART_CY + 240})`}>
        <rect x={0} y={0} width={480} height={108} rx={6}
          fill="rgba(2, 6, 23, 0.55)" stroke={PAI_THEME.colors.textDark} strokeWidth={1.2}/>
        <text x={240} y={26} fontSize={20} fill={PAI_THEME.colors.accentLight} textAnchor="middle" fontWeight={700}>
          Anatomy key
        </text>
        <g fontSize={15} fill={PAI_THEME.colors.text}>
          <circle cx={24} cy={46} r={7} fill={PAI_THEME.colors.oxygenated}/>
          <text x={38} y={50}>oxygenated (LA · LV · aorta)</text>

          <circle cx={24} cy={70} r={7} fill={PAI_THEME.colors.deoxygenated}/>
          <text x={38} y={74}>deoxygenated (RA · RV · pulmonary)</text>

          <line x1={16} y1={92} x2={32} y2={92} stroke={PAI_THEME.colors.valveOpen} strokeWidth={4} strokeLinecap="round"/>
          <text x={38} y={96}>valve open</text>

          <line x1={196} y1={92} x2={212} y2={92} stroke={PAI_THEME.colors.valveClosed} strokeWidth={4} strokeLinecap="round"/>
          <text x={218} y={96}>valve closed</text>
        </g>
      </g>
    </g>
  );
};

// ── PressureTracePanel — three waveforms scrolling out ───────────────────────
const PressureTracePanel: React.FC<{ frame: number }> = ({ frame }) => {
  // Build the waveforms for the trailing window of frames.
  // Show the past ~3 beats (216 frames) scrolling left to right.
  const WINDOW = BEAT_FRAMES * 3;
  const beatRel = frame - F_BEAT_START;
  const start = Math.max(0, beatRel - WINDOW);
  const end   = Math.max(0, beatRel);

  // Convert frame-in-beat → local
  const localOf = (b: number) => ((b % BEAT_FRAMES) + BEAT_FRAMES) % BEAT_FRAMES;

  // Generate points
  const tracePoints = (fn: (l: number) => number): string => {
    const pts: string[] = [];
    const span = WINDOW;
    for (let b = start; b <= end; b++) {
      const t = (b - start) / span;       // 0..1 across plot width
      const x = TRACE_X0 + t * (TRACE_X1 - TRACE_X0);
      const p = fn(localOf(b));
      // Out range swapped so high pressure = low y (screen down)
      const y = interpolate(p, [0, PRESSURE_MAX], [TRACE_Y_BOTTOM, TRACE_Y_TOP], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
      pts.push(`${x.toFixed(1)} ${y.toFixed(1)}`);
    }
    return pts.length > 0 ? `M ${pts.join(' L ')}` : '';
  };

  const aoPath = tracePoints(aorticPressure);
  const lvPath = tracePoints(ventricularPressure);
  const laPath = tracePoints(atrialPressure);

  return (
    <g>
      {/* Panel background */}
      <rect x={TRACE_X0 - 30} y={TRACE_Y_TOP - 70} width={(TRACE_X1 - TRACE_X0) + 70} height={(TRACE_Y_BOTTOM - TRACE_Y_TOP) + 110}
        rx={10} fill="rgba(2, 6, 23, 0.55)" stroke={PAI_THEME.colors.textDark} strokeWidth={1.4}/>

      <text x={(TRACE_X0 + TRACE_X1) / 2} y={TRACE_Y_TOP - 40} fontSize={26} fill={PAI_THEME.colors.text} textAnchor="middle" fontWeight={700}>
        Pressure traces — aortic · ventricular · atrial
      </text>
      <text x={(TRACE_X0 + TRACE_X1) / 2} y={TRACE_Y_TOP - 12} fontSize={16} fill={PAI_THEME.colors.textMuted} textAnchor="middle" fontStyle="italic">
        Wiggers diagram — 3-beat scrolling window
      </text>

      {/* Y-axis (pressure mmHg) */}
      <line x1={TRACE_X0} y1={TRACE_Y_TOP} x2={TRACE_X0} y2={TRACE_Y_BOTTOM} stroke={PAI_THEME.colors.textMuted} strokeWidth={1.2}/>
      {/* Y-ticks at 0, 40, 80, 120 mmHg */}
      {[0, 40, 80, 120].map((p) => {
        const y = interpolate(p, [0, PRESSURE_MAX], [TRACE_Y_BOTTOM, TRACE_Y_TOP], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
        return (
          <g key={p}>
            <line x1={TRACE_X0 - 6} y1={y} x2={TRACE_X0} y2={y} stroke={PAI_THEME.colors.textMuted} strokeWidth={1}/>
            <text x={TRACE_X0 - 12} y={y + 5} fontSize={14} fill={PAI_THEME.colors.textMuted} textAnchor="end">{p}</text>
          </g>
        );
      })}
      <text x={TRACE_X0 - 50} y={(TRACE_Y_TOP + TRACE_Y_BOTTOM) / 2}
        fontSize={14} fill={PAI_THEME.colors.textMuted}
        transform={`rotate(-90 ${TRACE_X0 - 50} ${(TRACE_Y_TOP + TRACE_Y_BOTTOM) / 2})`}
        textAnchor="middle">
        Pressure (mmHg)
      </text>

      {/* X-axis baseline */}
      <line x1={TRACE_X0} y1={TRACE_Y_BOTTOM} x2={TRACE_X1} y2={TRACE_Y_BOTTOM} stroke={PAI_THEME.colors.textMuted} strokeWidth={1.2}/>
      <text x={(TRACE_X0 + TRACE_X1) / 2} y={TRACE_Y_BOTTOM + 32} fontSize={14} fill={PAI_THEME.colors.textMuted} textAnchor="middle">
        time →
      </text>

      {/* Now line (right edge) */}
      <line x1={TRACE_X1} y1={TRACE_Y_TOP} x2={TRACE_X1} y2={TRACE_Y_BOTTOM} stroke={PAI_THEME.colors.warning} strokeWidth={1.2} strokeDasharray="4 3"/>
      <text x={TRACE_X1 + 6} y={TRACE_Y_TOP + 14} fontSize={12} fill={PAI_THEME.colors.warning} fontWeight={700}>now</text>

      {/* Traces */}
      <path d={aoPath} fill="none" stroke={PAI_THEME.colors.aorta}            strokeWidth={3}/>
      <path d={lvPath} fill="none" stroke={PAI_THEME.colors.ventricularEjection} strokeWidth={3}/>
      <path d={laPath} fill="none" stroke={PAI_THEME.colors.atrialSystole}    strokeWidth={2.5} strokeDasharray="6 4"/>

      {/* Legend inside panel */}
      <g transform={`translate(${TRACE_X0 + 16}, ${TRACE_Y_TOP + 14})`}>
        <line x1={0} y1={6} x2={28} y2={6} stroke={PAI_THEME.colors.aorta} strokeWidth={3}/>
        <text x={36} y={10} fontSize={14} fill={PAI_THEME.colors.text} fontWeight={700}>Aortic</text>

        <line x1={104} y1={6} x2={132} y2={6} stroke={PAI_THEME.colors.ventricularEjection} strokeWidth={3}/>
        <text x={140} y={10} fontSize={14} fill={PAI_THEME.colors.text} fontWeight={700}>LV</text>

        <line x1={180} y1={6} x2={208} y2={6} stroke={PAI_THEME.colors.atrialSystole} strokeWidth={2.5} strokeDasharray="6 4"/>
        <text x={216} y={10} fontSize={14} fill={PAI_THEME.colors.text} fontWeight={700}>LA</text>
      </g>
    </g>
  );
};

// ── PVLoopPanel — pressure-volume loop building up ───────────────────────────
const PVLoopPanel: React.FC<{ frame: number; beatIdx: number }> = ({ frame, beatIdx }) => {
  // Plot pressure (y) vs volume (x). Build up traced segments as the beat progresses.
  const xOf = (v: number) =>
    interpolate(v, [40, 140], [PV_X0 + 60, PV_X1 - 20], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const yOf = (p: number) =>
    // Swap output to invert: high pressure → high on screen (low y)
    interpolate(p, [0, PRESSURE_MAX], [PV_Y_BOTTOM - 20, PV_Y_TOP + 40], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  // Build path for the current and prior beats (up to last 3)
  const beatRel = Math.max(0, frame - F_BEAT_START);
  const currentBeat = Math.min(beatIdx, N_BEATS - 1);
  const currentLocal = beatRel % BEAT_FRAMES;

  // For each beat already complete, draw the full loop in faded colour
  const completedLoops: string[] = [];
  for (let b = 0; b < currentBeat; b++) {
    const pts: string[] = [];
    for (let l = 0; l <= BEAT_FRAMES; l += 2) {
      pts.push(`${xOf(ventricularVolume(l)).toFixed(1)} ${yOf(ventricularPressure(l)).toFixed(1)}`);
    }
    completedLoops.push(`M ${pts.join(' L ')}`);
  }
  // Current beat — only up to currentLocal
  const currentPts: string[] = [];
  for (let l = 0; l <= currentLocal; l += 1) {
    currentPts.push(`${xOf(ventricularVolume(l)).toFixed(1)} ${yOf(ventricularPressure(l)).toFixed(1)}`);
  }
  const currentPath = currentPts.length > 0 ? `M ${currentPts.join(' L ')}` : '';

  // Marker at the current point
  const curX = xOf(ventricularVolume(currentLocal));
  const curY = yOf(ventricularPressure(currentLocal));

  return (
    <g>
      {/* Panel background */}
      <rect x={PV_X0 - 30} y={PV_Y_TOP - 50} width={(PV_X1 - PV_X0) + 70} height={(PV_Y_BOTTOM - PV_Y_TOP) + 80}
        rx={10} fill="rgba(2, 6, 23, 0.55)" stroke={PAI_THEME.colors.textDark} strokeWidth={1.4}/>

      <text x={(PV_X0 + PV_X1) / 2} y={PV_Y_TOP - 22} fontSize={22} fill={PAI_THEME.colors.text} textAnchor="middle" fontWeight={700}>
        LV Pressure-Volume loop
      </text>

      {/* Axes */}
      <line x1={PV_X0 + 60} y1={PV_Y_BOTTOM - 20} x2={PV_X1 - 20} y2={PV_Y_BOTTOM - 20} stroke={PAI_THEME.colors.textMuted} strokeWidth={1.2}/>
      <line x1={PV_X0 + 60} y1={PV_Y_BOTTOM - 20} x2={PV_X0 + 60} y2={PV_Y_TOP + 40}    stroke={PAI_THEME.colors.textMuted} strokeWidth={1.2}/>

      {/* Volume ticks 50, 80, 110, 140 */}
      {[50, 80, 110, 140].map((v) => {
        const x = xOf(v);
        return (
          <g key={v}>
            <line x1={x} y1={PV_Y_BOTTOM - 20} x2={x} y2={PV_Y_BOTTOM - 14} stroke={PAI_THEME.colors.textMuted} strokeWidth={1}/>
            <text x={x} y={PV_Y_BOTTOM - 2} fontSize={12} fill={PAI_THEME.colors.textMuted} textAnchor="middle">{v}</text>
          </g>
        );
      })}
      <text x={(PV_X0 + PV_X1) / 2} y={PV_Y_BOTTOM + 14} fontSize={13} fill={PAI_THEME.colors.textMuted} textAnchor="middle">Volume (mL)</text>

      {/* Pressure ticks 0, 40, 80, 120 */}
      {[0, 40, 80, 120].map((p) => {
        const y = yOf(p);
        return (
          <g key={p}>
            <line x1={PV_X0 + 54} y1={y} x2={PV_X0 + 60} y2={y} stroke={PAI_THEME.colors.textMuted} strokeWidth={1}/>
            <text x={PV_X0 + 48} y={y + 4} fontSize={12} fill={PAI_THEME.colors.textMuted} textAnchor="end">{p}</text>
          </g>
        );
      })}

      {/* Completed loops (faded) */}
      {completedLoops.map((d, i) => (
        <path key={i} d={d} fill="none" stroke={PAI_THEME.colors.ventricularEjection} strokeWidth={1.5} opacity={0.25}/>
      ))}

      {/* Current loop in progress */}
      {currentPath && (
        <path d={currentPath} fill="none" stroke={PAI_THEME.colors.ventricularEjection} strokeWidth={2.6}/>
      )}

      {/* Current point marker */}
      {beatRel > 0 && (
        <circle cx={curX} cy={curY} r={6} fill={PAI_THEME.colors.warning} stroke={PAI_THEME.colors.text} strokeWidth={2}/>
      )}

      {/* Stroke volume annotation (lower-right of panel) */}
      <text x={PV_X1 - 24} y={PV_Y_BOTTOM - 60} fontSize={13} fill={PAI_THEME.colors.textMuted} textAnchor="end">
        SV = EDV - ESV ≈ 70 mL
      </text>
    </g>
  );
};

// ── Main scene ───────────────────────────────────────────────────────────────
export const CardiacCycleScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Title spring + opacity
  const titleSpring = spring({ frame, fps, config: PAI_THEME.animation.springDefault });
  const titleOp = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: 'clamp' });
  const subOp   = interpolate(frame, [20, 60], [0, 1], { extrapolateRight: 'clamp' });

  // Closing caption
  const closingOp = interpolate(frame, [F_BEAT_END, F_CLOSE_END], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  // Beat-relative state
  const { local, beatIdx } = getBeatLocal(frame);
  const phase = getPhase(local);
  const phaseInfo = PHASE_INFO[phase];

  // Phase caption fade — each phase its own quick fade-in
  const phaseStartLocal = (
    phase === 'AS' ? 0 :
    phase === 'IC' ? PH_AS_END :
    phase === 'VE' ? PH_IC_END :
    phase === 'IR' ? PH_VE_END :
                     PH_IR_END
  );
  const localSincePhase = local - phaseStartLocal;
  const phaseOp = interpolate(localSincePhase, [0, 6], [0.3, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  return (
    <AbsoluteFill style={{
      background: `linear-gradient(135deg, ${PAI_THEME.colors.background}, ${PAI_THEME.colors.backgroundAlt})`,
      fontFamily: PAI_THEME.typography.fontFamily,
    }}>
      {/* ── Title ─────────────────────────────────────────────── */}
      <div style={{
        position: 'absolute', top: 30, left: 0, right: 0, textAlign: 'center',
      }}>
        <h1 style={{
          fontSize: 56, color: PAI_THEME.colors.text, margin: 0,
          opacity: titleOp, transform: `scale(${titleSpring})`,
        }}>
          The Cardiac Cycle — One Heartbeat, Five Phases
        </h1>
        <p style={{
          fontSize: 24, color: PAI_THEME.colors.accentLight, marginTop: 4, fontStyle: 'italic',
          opacity: subOp,
        }}>
          Atrial systole → Isovolumetric contraction → Ventricular ejection → Isovolumetric relaxation → Ventricular filling
        </p>
      </div>

      {/* ── SVG layer ─────────────────────────────────────────── */}
      <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} style={{ position: 'absolute', inset: 0 }}>

        {/* Heart anatomy */}
        {frame >= F_TITLE_END - 20 && <HeartCrossSection local={local} phase={phase} />}

        {/* Pressure traces */}
        {frame >= F_TITLE_END && <PressureTracePanel frame={frame} />}

        {/* P-V loop */}
        {frame >= F_TITLE_END && <PVLoopPanel frame={frame} beatIdx={beatIdx} />}

        {/* Phase banner — centred between heart and traces */}
        {frame >= F_BEAT_START && frame < F_BEAT_END && (
          <g opacity={phaseOp}>
            <rect x={HEART_CX - 280} y={150} width={560} height={60} rx={10}
              fill={phaseInfo.color} opacity={0.92}
              stroke={PAI_THEME.colors.text} strokeWidth={2}/>
            <text x={HEART_CX} y={190} fontSize={30} fill={PAI_THEME.colors.text}
              textAnchor="middle" fontWeight={700}>
              {phaseInfo.label}
            </text>
          </g>
        )}

        {/* Beat counter (small, lower-left) */}
        {frame >= F_BEAT_START && (
          <text x={120} y={1020} fontSize={20} fill={PAI_THEME.colors.textMuted} fontWeight={700}>
            Beat {Math.min(beatIdx + 1, N_BEATS)} / {N_BEATS}  ·  HR ≈ 72 bpm (slowed 3×)
          </text>
        )}
      </svg>

      {/* ── Phase narration strip (bottom) ────────────────────── */}
      {frame >= F_BEAT_START && frame < F_BEAT_END && (
        <div style={{
          position: 'absolute', bottom: 32, left: 0, right: 0,
          textAlign: 'center', fontSize: 26, fontWeight: 600,
          color: PAI_THEME.colors.text, opacity: phaseOp,
        }}>
          {phaseInfo.narration}
        </div>
      )}

      {/* ── Closing caption ────────────────────────────────────── */}
      {frame >= F_BEAT_END && (
        <div style={{
          position: 'absolute', bottom: 0, top: 0, left: 0, right: 0,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          textAlign: 'center', padding: 80,
          fontSize: 44, fontWeight: 700,
          color: PAI_THEME.colors.text, opacity: closingOp,
          background: 'rgba(2, 6, 23, 0.55)',
        }}>
          <div>
            <div style={{ color: PAI_THEME.colors.accentLight, marginBottom: 30 }}>
              One beat ≈ 0.8 seconds.
            </div>
            <div style={{ fontSize: 32, fontWeight: 600 }}>
              Across a 75-year life that&apos;s about 3 billion beats —
            </div>
            <div style={{ fontSize: 32, fontWeight: 600, marginTop: 12 }}>
              every one of them this same five-phase sequence.
            </div>
          </div>
        </div>
      )}
    </AbsoluteFill>
  );
};
