/**
 * GalvanicCellScene — animated Daniell cell (Zn | Zn²⁺ ‖ Cu²⁺ | Cu).
 *
 * Story arc (30 fps, 28 s = 840 frames):
 *   0–60       title + subtitle fade in
 *   60–150     two beakers + electrolytes draw in; salt bridge slides into place;
 *              external wire + voltmeter appear; Zn / Cu electrode rods drop in
 *   150–240    half-reaction labels mount at each electrode
 *   240–600    continuous loop: electrons stream through wire (Zn → Cu);
 *              Zn²⁺ ions dissolve off anode into left beaker (oxidation);
 *              Cu²⁺ ions plate onto cathode from right beaker (reduction);
 *              Na⁺ migrates rightward through salt bridge, SO₄²⁻ migrates left
 *   240–840    voltmeter LCD lights up + ticks 0.00 → 1.10 V
 *   600–720    E°cell math reveal: 0.34 − (−0.76) = +1.10 V
 *   720–840    closing tag — "Spontaneous: ΔG° < 0 because E°cell > 0."
 *
 * CRITICAL Remotion gotcha avoided: every interpolate input range [a, b] is
 * strictly increasing. For values that should DECREASE as frame grows, the
 * OUTPUT range is reversed (e.g. dashoffset goes from CURVE_LENGTH → 0).
 */
import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate, spring, useVideoConfig } from 'remotion';
import { PAI_THEME } from '../theme';

// ── Geometry (1920 × 1080 stage) ──────────────────────────────────────────────
const STAGE_W = 1920;

// Beakers
const BEAKER_W = 380;
const BEAKER_H = 420;
const BEAKER_TOP = 540;        // y of beaker rim
const BEAKER_BOTTOM = BEAKER_TOP + BEAKER_H; // 960

const LEFT_BEAKER_CX = 480;
const RIGHT_BEAKER_CX = 1440;

const LEFT_BEAKER_X = LEFT_BEAKER_CX - BEAKER_W / 2;   // 290
const RIGHT_BEAKER_X = RIGHT_BEAKER_CX - BEAKER_W / 2; // 1250

// Electrolyte (fills most of beaker, leaves headspace)
const ELECTROLYTE_TOP = BEAKER_TOP + 60;     // 600
const ELECTROLYTE_BOTTOM = BEAKER_BOTTOM - 10; // 950

// Electrode rods
const ELECTRODE_W = 56;
const ELECTRODE_TOP = 440;            // protrudes above beaker rim
const ELECTRODE_BOTTOM = 920;         // submerged into electrolyte
const ZN_X = LEFT_BEAKER_CX;
const CU_X = RIGHT_BEAKER_CX;

// External wire path: top of Zn rod → up → across → down → top of Cu rod.
// Voltmeter sits centred at the top of the wire arc.
const WIRE_TOP_Y = 240;
const VM_CX = STAGE_W / 2;
const VM_CY = WIRE_TOP_Y - 20;
const VM_W = 220;
const VM_H = 110;

// Salt bridge — inverted-U glass tube linking the two beakers via the headspace.
const SB_LEFT_X = LEFT_BEAKER_CX + 100;
const SB_RIGHT_X = RIGHT_BEAKER_CX - 100;
const SB_TUBE_Y = BEAKER_TOP - 20;    // horizontal centreline of the U-tube top
const SB_DIP_LEFT_X = SB_LEFT_X;
const SB_DIP_RIGHT_X = SB_RIGHT_X;
const SB_DIP_BOTTOM_Y = ELECTROLYTE_TOP + 70; // tube dips into both electrolytes

// ── Frame anchors ────────────────────────────────────────────────────────────
const F_TITLE_END = 60;
const F_APPARATUS_IN = 60;
const F_APPARATUS_END = 150;
const F_LABELS_IN = 150;
const F_LABELS_END = 240;
const F_FLOW_IN = 240;
const F_FLOW_END = 600;
const F_VM_TICK_IN = 240;
const F_VM_TICK_END = 540;
const F_EMATH_IN = 600;
const F_EMATH_END = 720;
const F_TAG_IN = 720;
const F_TAG_END = 750;

// Wire path string — used for both the wire stroke and for the electron flow path.
// Goes UP from Zn rod top, ACROSS through voltmeter centre, DOWN to Cu rod top.
const WIRE_PATH = `
  M ${ZN_X} ${ELECTRODE_TOP}
  L ${ZN_X} ${WIRE_TOP_Y}
  L ${CU_X} ${WIRE_TOP_Y}
  L ${CU_X} ${ELECTRODE_TOP}
`;

// Generate a position along the simple polyline at parametric t∈[0,1].
// Segment 1: (ZN_X, ELECTRODE_TOP) → (ZN_X, WIRE_TOP_Y)        vertical UP
// Segment 2: (ZN_X, WIRE_TOP_Y)    → (CU_X, WIRE_TOP_Y)        horizontal RIGHT
// Segment 3: (CU_X, WIRE_TOP_Y)    → (CU_X, ELECTRODE_TOP)     vertical DOWN
const L1 = ELECTRODE_TOP - WIRE_TOP_Y;     // vertical leg length
const L2 = CU_X - ZN_X;                     // horizontal leg length
const L3 = ELECTRODE_TOP - WIRE_TOP_Y;     // vertical leg length
const L_TOTAL = L1 + L2 + L3;

const wirePos = (t: number) => {
  const d = t * L_TOTAL;
  if (d <= L1) {
    return { x: ZN_X, y: ELECTRODE_TOP - d };
  }
  if (d <= L1 + L2) {
    return { x: ZN_X + (d - L1), y: WIRE_TOP_Y };
  }
  return { x: CU_X, y: WIRE_TOP_Y + (d - L1 - L2) };
};

export const GalvanicCellScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // ── Title (0 → 60) ────────────────────────────────────────────────────────
  const titleScale = spring({ frame, fps, config: PAI_THEME.animation.springDefault });
  const titleOp = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: 'clamp' });
  const subOp = interpolate(frame, [20, F_TITLE_END], [0, 1], { extrapolateRight: 'clamp' });

  // Title shrinks slightly when tag appears — opacity reduces (decreasing output, increasing input range).
  const titlePersist = interpolate(frame, [F_TAG_IN, F_TAG_IN + 30], [1, 0.45], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });

  // ── Apparatus build (60 → 150) ────────────────────────────────────────────
  const apparatusOp = interpolate(frame, [F_APPARATUS_IN, F_APPARATUS_END], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });

  // Salt bridge slides down from above
  const saltBridgeDrop = interpolate(frame, [F_APPARATUS_IN + 20, F_APPARATUS_END], [-180, 0], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });

  // Electrode rods drop in (Zn first, then Cu)
  const znDrop = interpolate(frame, [F_APPARATUS_IN + 30, F_APPARATUS_IN + 75], [-300, 0], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });
  const cuDrop = interpolate(frame, [F_APPARATUS_IN + 45, F_APPARATUS_IN + 90], [-300, 0], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });

  // ── Half-reaction labels (150 → 240) ──────────────────────────────────────
  const labelsOp = interpolate(frame, [F_LABELS_IN, F_LABELS_END], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });

  // ── Electron flow (240 → 600) ─────────────────────────────────────────────
  // 6 electrons spaced evenly along the wire, looping every 90 frames (3 s).
  const ELECTRON_COUNT = 6;
  const LOOP_FRAMES = 90;
  const flowActive = frame >= F_FLOW_IN && frame <= F_FLOW_END + 60;
  const flowOp = interpolate(frame, [F_FLOW_IN, F_FLOW_IN + 20, F_FLOW_END, F_FLOW_END + 60], [0, 1, 1, 0], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });

  const electronPositions = [];
  if (flowActive) {
    const baseT = ((frame - F_FLOW_IN) / LOOP_FRAMES) % 1;
    for (let i = 0; i < ELECTRON_COUNT; i++) {
      const t = (baseT + i / ELECTRON_COUNT) % 1;
      electronPositions.push({ ...wirePos(t), key: i });
    }
  }

  // ── Zn²⁺ dissolution from anode (oxidation) ───────────────────────────────
  // Spawn ions periodically from the Zn rod into the left electrolyte.
  // We use a deterministic loop: each ion has a (spawnOffset) and travels for 90 frames.
  const ION_LIFETIME = 90;
  const ION_STAGGER = 30;
  const zincIons: { x: number; y: number; opacity: number; key: number }[] = [];
  if (flowActive) {
    for (let i = 0; i < 6; i++) {
      const localFrame = frame - F_FLOW_IN - i * ION_STAGGER;
      if (localFrame < 0) continue;
      const cycle = localFrame % ION_LIFETIME;
      const t = cycle / ION_LIFETIME; // 0 → 1
      // Start near surface of Zn rod, drift outward+down into the electrolyte
      const startX = ZN_X + (i % 2 === 0 ? -ELECTRODE_W / 2 - 6 : ELECTRODE_W / 2 + 6);
      const startY = ELECTROLYTE_TOP + 80 + (i * 17) % 180;
      const driftX = startX + (i % 2 === 0 ? -1 : 1) * 60 * t;
      const driftY = startY + 90 * t;
      // Fade in then out
      const opacity = interpolate(t, [0, 0.15, 0.85, 1], [0, 1, 1, 0]);
      zincIons.push({ x: driftX, y: driftY, opacity, key: i });
    }
  }

  // ── Cu²⁺ → Cu plating onto cathode (reduction) ────────────────────────────
  // Ions emerge from right electrolyte and drift toward Cu rod, then vanish (plated).
  const copperIons: { x: number; y: number; opacity: number; key: number }[] = [];
  if (flowActive) {
    for (let i = 0; i < 6; i++) {
      const localFrame = frame - F_FLOW_IN - i * ION_STAGGER - 15;
      if (localFrame < 0) continue;
      const cycle = localFrame % ION_LIFETIME;
      const t = cycle / ION_LIFETIME;
      // Spawn somewhere in the right electrolyte, drift toward Cu rod, then vanish
      const startX = CU_X + (i % 2 === 0 ? 120 : -120);
      const startY = ELECTROLYTE_TOP + 60 + (i * 23) % 200;
      const targetX = CU_X + (i % 2 === 0 ? ELECTRODE_W / 2 + 6 : -ELECTRODE_W / 2 - 6);
      const targetY = startY;
      const x = startX + (targetX - startX) * t;
      const y = startY + (targetY - startY) * t;
      const opacity = interpolate(t, [0, 0.15, 0.8, 1], [0, 1, 1, 0]);
      copperIons.push({ x, y, opacity, key: i });
    }
  }

  // ── Salt bridge ion migration ─────────────────────────────────────────────
  // Na⁺ moves RIGHT through tube toward cathode beaker.
  // SO₄²⁻ moves LEFT through tube toward anode beaker.
  const SB_LIFETIME = 120;
  const SB_STAGGER = 30;
  const naIons: { x: number; y: number; opacity: number; key: number }[] = [];
  const so4Ions: { x: number; y: number; opacity: number; key: number }[] = [];
  if (flowActive) {
    for (let i = 0; i < 4; i++) {
      const localFrame = frame - F_FLOW_IN - i * SB_STAGGER;
      if (localFrame < 0) continue;
      const cycle = localFrame % SB_LIFETIME;
      const t = cycle / SB_LIFETIME;
      // Na⁺ path: starts in left beaker headspace, climbs up left side of tube,
      // crosses tube top moving right, descends into right beaker.
      // We'll simulate the tube as 3 segments (up, across, down) and parametrise.
      const naX = SB_DIP_LEFT_X + (SB_DIP_RIGHT_X - SB_DIP_LEFT_X) * t;
      const naY = SB_TUBE_Y + Math.sin(t * Math.PI) * -40 + 0; // gentle arc within the tube
      naIons.push({
        x: naX,
        y: naY,
        opacity: interpolate(t, [0, 0.1, 0.9, 1], [0, 1, 1, 0]),
        key: i,
      });

      // SO₄²⁻ moves opposite direction, slightly offset Y for visual separation.
      const so4t = t;
      const so4X = SB_DIP_RIGHT_X + (SB_DIP_LEFT_X - SB_DIP_RIGHT_X) * so4t;
      const so4Y = SB_TUBE_Y + Math.sin(so4t * Math.PI) * -40 + 20;
      so4Ions.push({
        x: so4X,
        y: so4Y,
        opacity: interpolate(so4t, [0, 0.1, 0.9, 1], [0, 1, 1, 0]),
        key: i + 10,
      });
    }
  }

  // ── Voltmeter tick from 0.00 → 1.10 V (240 → 540) ─────────────────────────
  const vmReading = interpolate(frame, [F_VM_TICK_IN, F_VM_TICK_END], [0, 1.10], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });
  const vmGlow = interpolate(frame, [F_VM_TICK_IN, F_VM_TICK_IN + 20], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });

  // ── E°cell math reveal (600 → 720) ────────────────────────────────────────
  const emathOp = interpolate(frame, [F_EMATH_IN, F_EMATH_END], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });

  // ── Closing tag (720 → 840) ───────────────────────────────────────────────
  const tagOp = interpolate(frame, [F_TAG_IN, F_TAG_END], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(135deg, ${PAI_THEME.colors.background}, ${PAI_THEME.colors.backgroundAlt})`,
        fontFamily: PAI_THEME.typography.fontFamily,
      }}
    >
      {/* ── Title ─────────────────────────────────────────────── */}
      <div
        style={{
          position: 'absolute',
          top: 28,
          left: 0,
          right: 0,
          textAlign: 'center',
          opacity: titleOp * titlePersist,
        }}
      >
        <h1
          style={{
            fontSize: 54,
            color: PAI_THEME.colors.text,
            margin: 0,
            transform: `scale(${titleScale})`,
          }}
        >
          Galvanic Cell — Electrons Do the Work
        </h1>
        <p
          style={{
            fontSize: 24,
            color: PAI_THEME.colors.accentLight,
            marginTop: 4,
            fontStyle: 'italic',
            opacity: subOp,
          }}
        >
          Zn | Zn²⁺ ‖ Cu²⁺ | Cu     ·     E°cell = +1.10 V     ·     spontaneous
        </p>
      </div>

      {/* ── Main SVG stage ──────────────────────────────────── */}
      <svg
        width={1920}
        height={1080}
        viewBox="0 0 1920 1080"
        style={{ position: 'absolute', inset: 0 }}
      >
        <defs>
          {/* Glow filter for moving electrons */}
          <radialGradient id="rx-electron-glow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor={PAI_THEME.colors.electronGlow} stopOpacity={1} />
            <stop offset="60%" stopColor={PAI_THEME.colors.electronGlow} stopOpacity={0.5} />
            <stop offset="100%" stopColor={PAI_THEME.colors.electronGlow} stopOpacity={0} />
          </radialGradient>
          {/* Zinc electrolyte gradient — pale blue */}
          <linearGradient id="rx-zn-elec" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={PAI_THEME.colors.zincSolution} />
            <stop offset="100%" stopColor="rgba(165, 180, 252, 0.55)" />
          </linearGradient>
          {/* Copper electrolyte gradient — deeper blue */}
          <linearGradient id="rx-cu-elec" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={PAI_THEME.colors.copperSolution} />
            <stop offset="100%" stopColor="rgba(59, 130, 246, 0.75)" />
          </linearGradient>
          {/* Zn electrode metal gradient */}
          <linearGradient id="rx-zn-rod" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor={PAI_THEME.colors.zincDark} />
            <stop offset="50%" stopColor={PAI_THEME.colors.zinc} />
            <stop offset="100%" stopColor={PAI_THEME.colors.zincDark} />
          </linearGradient>
          {/* Cu electrode metal gradient */}
          <linearGradient id="rx-cu-rod" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor={PAI_THEME.colors.copperDark} />
            <stop offset="50%" stopColor={PAI_THEME.colors.copper} />
            <stop offset="100%" stopColor={PAI_THEME.colors.copperDark} />
          </linearGradient>
          {/* Arrow markers for current direction */}
          <marker id="rx-arrow" viewBox="0 0 10 10" refX={8} refY={5} markerWidth={6} markerHeight={6} orient="auto">
            <path d="M 0 0 L 10 5 L 0 10 z" fill={PAI_THEME.colors.electronGlow} />
          </marker>
        </defs>

        {/* ── External wire (drawn first, electrodes overlay) ── */}
        <g opacity={apparatusOp}>
          <path
            d={WIRE_PATH}
            fill="none"
            stroke={PAI_THEME.colors.wireColor}
            strokeWidth={6}
            strokeLinecap="round"
          />
        </g>

        {/* ── Left beaker (Zn | ZnSO₄) ───────────────────────── */}
        <g opacity={apparatusOp}>
          {/* Beaker glass — outlined rectangle with rounded bottom */}
          <path
            d={`
              M ${LEFT_BEAKER_X} ${BEAKER_TOP}
              L ${LEFT_BEAKER_X} ${BEAKER_BOTTOM - 30}
              Q ${LEFT_BEAKER_X} ${BEAKER_BOTTOM} ${LEFT_BEAKER_X + 30} ${BEAKER_BOTTOM}
              L ${LEFT_BEAKER_X + BEAKER_W - 30} ${BEAKER_BOTTOM}
              Q ${LEFT_BEAKER_X + BEAKER_W} ${BEAKER_BOTTOM} ${LEFT_BEAKER_X + BEAKER_W} ${BEAKER_BOTTOM - 30}
              L ${LEFT_BEAKER_X + BEAKER_W} ${BEAKER_TOP}
            `}
            fill="rgba(255, 255, 255, 0.04)"
            stroke={PAI_THEME.colors.text}
            strokeWidth={3}
          />
          {/* Electrolyte fill */}
          <path
            d={`
              M ${LEFT_BEAKER_X + 4} ${ELECTROLYTE_TOP}
              L ${LEFT_BEAKER_X + 4} ${BEAKER_BOTTOM - 30}
              Q ${LEFT_BEAKER_X + 4} ${BEAKER_BOTTOM - 4} ${LEFT_BEAKER_X + 30} ${BEAKER_BOTTOM - 4}
              L ${LEFT_BEAKER_X + BEAKER_W - 30} ${BEAKER_BOTTOM - 4}
              Q ${LEFT_BEAKER_X + BEAKER_W - 4} ${BEAKER_BOTTOM - 4} ${LEFT_BEAKER_X + BEAKER_W - 4} ${BEAKER_BOTTOM - 30}
              L ${LEFT_BEAKER_X + BEAKER_W - 4} ${ELECTROLYTE_TOP}
              Z
            `}
            fill="url(#rx-zn-elec)"
          />
          {/* Solution label */}
          <text
            x={LEFT_BEAKER_CX}
            y={BEAKER_BOTTOM + 40}
            fill={PAI_THEME.colors.text}
            fontSize={24}
            fontWeight={700}
            textAnchor="middle"
          >
            1 M ZnSO₄
          </text>
        </g>

        {/* ── Right beaker (Cu²⁺ | Cu) ───────────────────────── */}
        <g opacity={apparatusOp}>
          <path
            d={`
              M ${RIGHT_BEAKER_X} ${BEAKER_TOP}
              L ${RIGHT_BEAKER_X} ${BEAKER_BOTTOM - 30}
              Q ${RIGHT_BEAKER_X} ${BEAKER_BOTTOM} ${RIGHT_BEAKER_X + 30} ${BEAKER_BOTTOM}
              L ${RIGHT_BEAKER_X + BEAKER_W - 30} ${BEAKER_BOTTOM}
              Q ${RIGHT_BEAKER_X + BEAKER_W} ${BEAKER_BOTTOM} ${RIGHT_BEAKER_X + BEAKER_W} ${BEAKER_BOTTOM - 30}
              L ${RIGHT_BEAKER_X + BEAKER_W} ${BEAKER_TOP}
            `}
            fill="rgba(255, 255, 255, 0.04)"
            stroke={PAI_THEME.colors.text}
            strokeWidth={3}
          />
          <path
            d={`
              M ${RIGHT_BEAKER_X + 4} ${ELECTROLYTE_TOP}
              L ${RIGHT_BEAKER_X + 4} ${BEAKER_BOTTOM - 30}
              Q ${RIGHT_BEAKER_X + 4} ${BEAKER_BOTTOM - 4} ${RIGHT_BEAKER_X + 30} ${BEAKER_BOTTOM - 4}
              L ${RIGHT_BEAKER_X + BEAKER_W - 30} ${BEAKER_BOTTOM - 4}
              Q ${RIGHT_BEAKER_X + BEAKER_W - 4} ${BEAKER_BOTTOM - 4} ${RIGHT_BEAKER_X + BEAKER_W - 4} ${BEAKER_BOTTOM - 30}
              L ${RIGHT_BEAKER_X + BEAKER_W - 4} ${ELECTROLYTE_TOP}
              Z
            `}
            fill="url(#rx-cu-elec)"
          />
          <text
            x={RIGHT_BEAKER_CX}
            y={BEAKER_BOTTOM + 40}
            fill={PAI_THEME.colors.text}
            fontSize={24}
            fontWeight={700}
            textAnchor="middle"
          >
            1 M CuSO₄
          </text>
        </g>

        {/* ── Salt bridge (inverted U between beakers) ─────── */}
        <g
          opacity={apparatusOp}
          transform={`translate(0 ${saltBridgeDrop})`}
        >
          {/* Glass tube outline */}
          <path
            d={`
              M ${SB_DIP_LEFT_X - 22} ${SB_DIP_BOTTOM_Y}
              L ${SB_DIP_LEFT_X - 22} ${SB_TUBE_Y - 28}
              Q ${SB_DIP_LEFT_X - 22} ${SB_TUBE_Y - 58} ${SB_DIP_LEFT_X + 8} ${SB_TUBE_Y - 58}
              L ${SB_DIP_RIGHT_X - 8} ${SB_TUBE_Y - 58}
              Q ${SB_DIP_RIGHT_X + 22} ${SB_TUBE_Y - 58} ${SB_DIP_RIGHT_X + 22} ${SB_TUBE_Y - 28}
              L ${SB_DIP_RIGHT_X + 22} ${SB_DIP_BOTTOM_Y}
              L ${SB_DIP_RIGHT_X - 22} ${SB_DIP_BOTTOM_Y}
              L ${SB_DIP_RIGHT_X - 22} ${SB_TUBE_Y - 28}
              L ${SB_DIP_LEFT_X + 22} ${SB_TUBE_Y - 28}
              L ${SB_DIP_LEFT_X + 22} ${SB_DIP_BOTTOM_Y}
              Z
            `}
            fill={PAI_THEME.colors.saltBridge}
            stroke={PAI_THEME.colors.saltBridgeDark}
            strokeWidth={2.5}
            opacity={0.85}
          />
          {/* Salt bridge label */}
          <text
            x={STAGE_W / 2}
            y={SB_TUBE_Y - 72}
            fill={PAI_THEME.colors.saltBridgeDark}
            fontSize={22}
            fontWeight={700}
            textAnchor="middle"
          >
            salt bridge (Na₂SO₄ in agar)
          </text>
        </g>

        {/* ── Zn electrode (anode) ────────────────────────── */}
        <g transform={`translate(0 ${znDrop})`} opacity={apparatusOp}>
          <rect
            x={ZN_X - ELECTRODE_W / 2}
            y={ELECTRODE_TOP}
            width={ELECTRODE_W}
            height={ELECTRODE_BOTTOM - ELECTRODE_TOP}
            fill="url(#rx-zn-rod)"
            stroke={PAI_THEME.colors.text}
            strokeWidth={1.5}
            rx={4}
          />
          {/* Anode (−) marker */}
          <text
            x={ZN_X - 110}
            y={ELECTRODE_TOP + 30}
            fill={PAI_THEME.colors.error}
            fontSize={32}
            fontWeight={900}
            textAnchor="middle"
          >
            −
          </text>
          <text
            x={ZN_X - 110}
            y={ELECTRODE_TOP + 56}
            fill={PAI_THEME.colors.textMuted}
            fontSize={20}
            textAnchor="middle"
          >
            anode
          </text>
          <text
            x={ZN_X}
            y={ELECTRODE_TOP - 14}
            fill={PAI_THEME.colors.text}
            fontSize={28}
            fontWeight={800}
            textAnchor="middle"
          >
            Zn
          </text>
        </g>

        {/* ── Cu electrode (cathode) ─────────────────────── */}
        <g transform={`translate(0 ${cuDrop})`} opacity={apparatusOp}>
          <rect
            x={CU_X - ELECTRODE_W / 2}
            y={ELECTRODE_TOP}
            width={ELECTRODE_W}
            height={ELECTRODE_BOTTOM - ELECTRODE_TOP}
            fill="url(#rx-cu-rod)"
            stroke={PAI_THEME.colors.text}
            strokeWidth={1.5}
            rx={4}
          />
          <text
            x={CU_X + 110}
            y={ELECTRODE_TOP + 30}
            fill={PAI_THEME.colors.success}
            fontSize={32}
            fontWeight={900}
            textAnchor="middle"
          >
            +
          </text>
          <text
            x={CU_X + 110}
            y={ELECTRODE_TOP + 56}
            fill={PAI_THEME.colors.textMuted}
            fontSize={20}
            textAnchor="middle"
          >
            cathode
          </text>
          <text
            x={CU_X}
            y={ELECTRODE_TOP - 14}
            fill={PAI_THEME.colors.text}
            fontSize={28}
            fontWeight={800}
            textAnchor="middle"
          >
            Cu
          </text>
        </g>

        {/* ── Voltmeter ─────────────────────────────────── */}
        <g opacity={apparatusOp}>
          <rect
            x={VM_CX - VM_W / 2}
            y={VM_CY - VM_H / 2}
            width={VM_W}
            height={VM_H}
            fill={PAI_THEME.colors.backgroundAlt}
            stroke={PAI_THEME.colors.text}
            strokeWidth={3}
            rx={12}
          />
          <text
            x={VM_CX}
            y={VM_CY - 22}
            fill={PAI_THEME.colors.textMuted}
            fontSize={18}
            fontWeight={600}
            textAnchor="middle"
          >
            V
          </text>
          {/* LCD reading */}
          <rect
            x={VM_CX - VM_W / 2 + 20}
            y={VM_CY - 10}
            width={VM_W - 40}
            height={56}
            fill={PAI_THEME.colors.backgroundDark}
            stroke={PAI_THEME.colors.voltmeter}
            strokeWidth={2}
            rx={6}
            opacity={0.5 + 0.5 * vmGlow}
          />
          <text
            x={VM_CX}
            y={VM_CY + 32}
            fill={PAI_THEME.colors.voltmeter}
            fontSize={40}
            fontWeight={800}
            textAnchor="middle"
            fontFamily="monospace"
            style={{
              filter: vmGlow > 0.5 ? `drop-shadow(0 0 8px ${PAI_THEME.colors.voltmeter})` : undefined,
            }}
          >
            {vmReading.toFixed(2)} V
          </text>
        </g>

        {/* ── Current direction arrow on top wire (right-to-left for conventional current; electrons go LEFT-to-RIGHT actually go FROM Zn TO Cu, i.e. left to right) ── */}
        {flowOp > 0 && (
          <g opacity={flowOp}>
            <text
              x={VM_CX}
              y={WIRE_TOP_Y - 36}
              fill={PAI_THEME.colors.electronGlow}
              fontSize={22}
              fontWeight={700}
              textAnchor="middle"
            >
              e⁻ flow  →
            </text>
          </g>
        )}

        {/* ── Electrons travelling along wire (Zn → Cu) ──── */}
        {electronPositions.map((p) => (
          <g key={`e-${p.key}`} opacity={flowOp}>
            <circle cx={p.x} cy={p.y} r={18} fill="url(#rx-electron-glow)" />
            <circle
              cx={p.x}
              cy={p.y}
              r={8}
              fill={PAI_THEME.colors.electron}
              stroke={PAI_THEME.colors.text}
              strokeWidth={1.5}
            />
            <text
              x={p.x}
              y={p.y + 4}
              fill={PAI_THEME.colors.text}
              fontSize={11}
              fontWeight={700}
              textAnchor="middle"
            >
              e⁻
            </text>
          </g>
        ))}

        {/* ── Zn²⁺ ions dissolving from anode ────────────── */}
        {zincIons.map((ion) => (
          <g key={`zn-${ion.key}`} opacity={ion.opacity * flowOp}>
            <circle
              cx={ion.x}
              cy={ion.y}
              r={13}
              fill={PAI_THEME.colors.zinc}
              stroke={PAI_THEME.colors.text}
              strokeWidth={1.5}
            />
            <text
              x={ion.x}
              y={ion.y + 4}
              fill={PAI_THEME.colors.background}
              fontSize={11}
              fontWeight={700}
              textAnchor="middle"
            >
              Zn²⁺
            </text>
          </g>
        ))}

        {/* ── Cu²⁺ ions plating onto cathode ─────────────── */}
        {copperIons.map((ion) => (
          <g key={`cu-${ion.key}`} opacity={ion.opacity * flowOp}>
            <circle
              cx={ion.x}
              cy={ion.y}
              r={13}
              fill={PAI_THEME.colors.copper}
              stroke={PAI_THEME.colors.text}
              strokeWidth={1.5}
            />
            <text
              x={ion.x}
              y={ion.y + 4}
              fill={PAI_THEME.colors.text}
              fontSize={11}
              fontWeight={700}
              textAnchor="middle"
            >
              Cu²⁺
            </text>
          </g>
        ))}

        {/* ── Na⁺ migrating right through salt bridge ───── */}
        {naIons.map((ion) => (
          <g key={`na-${ion.key}`} opacity={ion.opacity * flowOp}>
            <circle
              cx={ion.x}
              cy={ion.y}
              r={10}
              fill={PAI_THEME.colors.sodiumIon}
              stroke={PAI_THEME.colors.text}
              strokeWidth={1.2}
            />
            <text
              x={ion.x}
              y={ion.y + 4}
              fill={PAI_THEME.colors.background}
              fontSize={10}
              fontWeight={700}
              textAnchor="middle"
            >
              Na⁺
            </text>
          </g>
        ))}

        {/* ── SO₄²⁻ migrating left through salt bridge ──── */}
        {so4Ions.map((ion) => (
          <g key={`so4-${ion.key}`} opacity={ion.opacity * flowOp}>
            <circle
              cx={ion.x}
              cy={ion.y}
              r={11}
              fill={PAI_THEME.colors.sulfateIon}
              stroke={PAI_THEME.colors.text}
              strokeWidth={1.2}
            />
            <text
              x={ion.x}
              y={ion.y + 4}
              fill={PAI_THEME.colors.text}
              fontSize={9}
              fontWeight={700}
              textAnchor="middle"
            >
              SO₄²⁻
            </text>
          </g>
        ))}

        {/* ── Half-reaction labels ───────────────────────── */}
        <g opacity={labelsOp}>
          {/* Anode half-reaction */}
          <rect
            x={120}
            y={ELECTRODE_BOTTOM + 80}
            width={680}
            height={84}
            rx={10}
            fill={PAI_THEME.colors.backgroundAlt}
            stroke={PAI_THEME.colors.error}
            strokeWidth={2.5}
          />
          <text
            x={460}
            y={ELECTRODE_BOTTOM + 110}
            fill={PAI_THEME.colors.error}
            fontSize={20}
            fontWeight={700}
            textAnchor="middle"
          >
            OXIDATION (anode)
          </text>
          <text
            x={460}
            y={ELECTRODE_BOTTOM + 144}
            fill={PAI_THEME.colors.text}
            fontSize={26}
            fontWeight={700}
            textAnchor="middle"
          >
            Zn(s) → Zn²⁺(aq) + 2e⁻       E° = +0.76 V
          </text>

          {/* Cathode half-reaction */}
          <rect
            x={1120}
            y={ELECTRODE_BOTTOM + 80}
            width={680}
            height={84}
            rx={10}
            fill={PAI_THEME.colors.backgroundAlt}
            stroke={PAI_THEME.colors.success}
            strokeWidth={2.5}
          />
          <text
            x={1460}
            y={ELECTRODE_BOTTOM + 110}
            fill={PAI_THEME.colors.success}
            fontSize={20}
            fontWeight={700}
            textAnchor="middle"
          >
            REDUCTION (cathode)
          </text>
          <text
            x={1460}
            y={ELECTRODE_BOTTOM + 144}
            fill={PAI_THEME.colors.text}
            fontSize={26}
            fontWeight={700}
            textAnchor="middle"
          >
            Cu²⁺(aq) + 2e⁻ → Cu(s)       E° = +0.34 V
          </text>
        </g>

        {/* ── E°cell math reveal (between the two half-reaction cards) ── */}
        <g opacity={emathOp}>
          <rect
            x={820}
            y={ELECTRODE_BOTTOM + 80}
            width={280}
            height={84}
            rx={10}
            fill={PAI_THEME.colors.warmWash}
            stroke={PAI_THEME.colors.warning}
            strokeWidth={3}
          />
          <text
            x={960}
            y={ELECTRODE_BOTTOM + 110}
            fill={PAI_THEME.colors.warning}
            fontSize={18}
            fontWeight={700}
            textAnchor="middle"
          >
            E°cell
          </text>
          <text
            x={960}
            y={ELECTRODE_BOTTOM + 144}
            fill={PAI_THEME.colors.text}
            fontSize={28}
            fontWeight={800}
            textAnchor="middle"
          >
            +1.10 V
          </text>
        </g>
      </svg>

      {/* ── E°cell math (mid-screen, above electrodes) ───────────── */}
      <div
        style={{
          position: 'absolute',
          top: 130,
          left: 0,
          right: 0,
          textAlign: 'center',
          opacity: emathOp,
        }}
      >
        <div
          style={{
            display: 'inline-block',
            padding: '14px 32px',
            borderRadius: 14,
            background: PAI_THEME.colors.warmWash,
            border: `2.5px solid ${PAI_THEME.colors.warning}`,
          }}
        >
          <div style={{ fontSize: 26, fontWeight: 700, color: PAI_THEME.colors.text }}>
            E°cell = E°cathode − E°anode = (+0.34) − (−0.76) = <span style={{ color: PAI_THEME.colors.warning }}>+1.10 V</span>
          </div>
        </div>
      </div>

      {/* ── Closing tag ─────────────────────────────────────────── */}
      <div
        style={{
          position: 'absolute',
          bottom: 28,
          left: 0,
          right: 0,
          textAlign: 'center',
          opacity: tagOp,
        }}
      >
        <div
          style={{
            display: 'inline-block',
            padding: '18px 40px',
            borderRadius: 18,
            background: PAI_THEME.colors.coolWash,
            border: `3px solid ${PAI_THEME.colors.accent}`,
          }}
        >
          <div style={{ fontSize: 32, fontWeight: 700, color: PAI_THEME.colors.text }}>
            E°cell &gt; 0   ⇒   ΔG° &lt; 0   ⇒   <span style={{ color: PAI_THEME.colors.success }}>spontaneous</span>
          </div>
          <div style={{ fontSize: 20, color: PAI_THEME.colors.textMuted, marginTop: 6 }}>
            Electrons travel through the wire; ions travel through the salt bridge — together they close the circuit.
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
