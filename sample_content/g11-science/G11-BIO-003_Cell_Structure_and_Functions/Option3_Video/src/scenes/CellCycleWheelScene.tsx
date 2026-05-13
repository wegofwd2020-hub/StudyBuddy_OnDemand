/**
 * CellCycleWheelScene — Animated cell-cycle wheel.
 *
 * Frames @ 30 fps (32 s total = 960 frames):
 *   0–60     Title fades in
 *   60–240   G1 phase — wheel hand sweeps; cell on stage grows; chromatin diffuse
 *   240–420  S phase — DNA replicates; chromatin doubles
 *   420–540  G2 phase — cell preps; chromatin still diffuse but now twice the DNA
 *   540–840  M phase — chromosomes condense, line up at metaphase plate, sister
 *                     chromatids separate (anaphase), cell pinches in two
 *                     (cytokinesis); two daughter cells emerge
 *   840–960  Closing caption fades in
 *
 * Visual structure (1920 × 1080):
 *   - Left half (≈ x 80–880): cell-cycle wheel with rotating hand and active wedge
 *   - Right half (≈ x 1000–1880): "stage" showing the cell at the active phase,
 *                                 with chromosomes and spindle as appropriate
 *   - Top: title strip
 *   - Bottom: caption strip with phase narration
 */
import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate, spring, useVideoConfig } from 'remotion';
import { PAI_THEME } from '../theme';

// ── Frame anchors ────────────────────────────────────────────────────────────
const F_TITLE_END = 60;
const F_G1_END    = 240;
const F_S_END     = 420;
const F_G2_END    = 540;
const F_M_END     = 840;
const F_CAPTION_START = F_M_END;
const F_CAPTION_END   = 960;

// Sub-anchors inside M-phase (540 → 840 = 300 frames)
const F_M_PROPHASE_END     = 600;  // 60 frames — condense
const F_M_METAPHASE_END    = 660;  // 60 frames — line up
const F_M_ANAPHASE_END     = 720;  // 60 frames — separate
const F_M_TELOPHASE_END    = 780;  // 60 frames — reform envelopes
const F_M_CYTOKINESIS_END  = 840;  // 60 frames — pinch + split

// ── Layout ───────────────────────────────────────────────────────────────────
const W = 1920;
const H = 1080;

const WHEEL_CX = 540;
const WHEEL_CY = 580;
const WHEEL_R  = 320;

const STAGE_CX = 1380;
const STAGE_CY = 580;
const STAGE_R  = 320;

// ── Phase wedge data ─────────────────────────────────────────────────────────
type Phase = 'G1' | 'S' | 'G2' | 'M';

type Wedge = {
  key: Phase;
  startAngle: number;  // radians, 0 = 12 o'clock, going clockwise
  endAngle: number;
  color: string;
  label: string;
  hint: string;
  duration: string;
};

// Wedge sizes proportional to canonical durations (G1 11h · S 8h · G2 4h · M 1h)
const TOTAL_HOURS = 24;
const HRS = { G1: 11, S: 8, G2: 4, M: 1 };
const ANG_PER_HR = (Math.PI * 2) / TOTAL_HOURS;

const WEDGES: Wedge[] = [
  {
    key: 'G1',
    startAngle: 0,
    endAngle: HRS.G1 * ANG_PER_HR,
    color: PAI_THEME.colors.g1,
    label: 'G₁  ·  Gap 1',
    hint: 'cell grows · organelles duplicate',
    duration: '~11 hr',
  },
  {
    key: 'S',
    startAngle: HRS.G1 * ANG_PER_HR,
    endAngle: (HRS.G1 + HRS.S) * ANG_PER_HR,
    color: PAI_THEME.colors.s,
    label: 'S  ·  Synthesis',
    hint: 'DNA replicates · 46 → 92 chromatids',
    duration: '~8 hr',
  },
  {
    key: 'G2',
    startAngle: (HRS.G1 + HRS.S) * ANG_PER_HR,
    endAngle: (HRS.G1 + HRS.S + HRS.G2) * ANG_PER_HR,
    color: PAI_THEME.colors.g2,
    label: 'G₂  ·  Gap 2',
    hint: 'spindle proteins · DNA damage check',
    duration: '~4 hr',
  },
  {
    key: 'M',
    startAngle: (HRS.G1 + HRS.S + HRS.G2) * ANG_PER_HR,
    endAngle: Math.PI * 2,
    color: PAI_THEME.colors.m,
    label: 'M  ·  Mitosis + Cytokinesis',
    hint: 'condense · align · separate · split',
    duration: '~1 hr',
  },
];

// ── Helpers ──────────────────────────────────────────────────────────────────
const polar = (cx: number, cy: number, r: number, angle: number) => ({
  // angle 0 = 12 o'clock (up), going clockwise
  x: cx + r * Math.sin(angle),
  y: cy - r * Math.cos(angle),
});

const wedgePath = (
  cx: number, cy: number, rOuter: number, rInner: number,
  start: number, end: number,
): string => {
  const oA = polar(cx, cy, rOuter, start);
  const oB = polar(cx, cy, rOuter, end);
  const iA = polar(cx, cy, rInner, end);
  const iB = polar(cx, cy, rInner, start);
  const largeArc = end - start > Math.PI ? 1 : 0;
  return [
    `M ${oA.x} ${oA.y}`,
    `A ${rOuter} ${rOuter} 0 ${largeArc} 1 ${oB.x} ${oB.y}`,
    `L ${iA.x} ${iA.y}`,
    `A ${rInner} ${rInner} 0 ${largeArc} 0 ${iB.x} ${iB.y}`,
    'Z',
  ].join(' ');
};

const getActivePhase = (frame: number): Phase => {
  if (frame < F_G1_END) return 'G1';
  if (frame < F_S_END)  return 'S';
  if (frame < F_G2_END) return 'G2';
  return 'M';
};

// Map frame → fraction of cycle traversed (0..1)
const cycleProgress = (frame: number): number => {
  // The hand sweeps from F_TITLE_END to F_M_END across the full circle.
  // Within that span it moves at non-uniform speed — proportional to wedge duration.
  if (frame <= F_TITLE_END) return 0;
  if (frame >= F_M_END) return 1;

  // Treat the four phase windows as constant-angular-speed within their wedge.
  if (frame < F_G1_END) {
    const t = (frame - F_TITLE_END) / (F_G1_END - F_TITLE_END);
    return (HRS.G1 / TOTAL_HOURS) * t;
  }
  if (frame < F_S_END) {
    const t = (frame - F_G1_END) / (F_S_END - F_G1_END);
    return (HRS.G1 + HRS.S * t) / TOTAL_HOURS;
  }
  if (frame < F_G2_END) {
    const t = (frame - F_S_END) / (F_G2_END - F_S_END);
    return (HRS.G1 + HRS.S + HRS.G2 * t) / TOTAL_HOURS;
  }
  // M-phase
  const t = (frame - F_G2_END) / (F_M_END - F_G2_END);
  return (HRS.G1 + HRS.S + HRS.G2 + HRS.M * t) / TOTAL_HOURS;
};

// ── Stage cell renderer ──────────────────────────────────────────────────────

type ChromatinState = 'diffuse-1n' | 'diffuse-2n' | 'condensed' | 'aligned' | 'separating' | 'separated';

const StageCell: React.FC<{
  frame: number;
}> = ({ frame }) => {
  const phase = getActivePhase(frame);

  // Cell radius grows during G1 (40 → 56), holds in S/G2/M-prophase, then we transition to two daughters
  const cellR = (() => {
    if (phase === 'G1') {
      return interpolate(frame, [F_TITLE_END, F_G1_END], [200, 240], {
        extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
      });
    }
    if (phase === 'S' || phase === 'G2') return 240;
    // M phase: gentle wobble (cell elongates in anaphase)
    if (frame < F_M_ANAPHASE_END) return 240;
    return 240;
  })();

  // For anaphase/telophase/cytokinesis, cell elongates horizontally
  const cellRX = (() => {
    if (frame < F_M_ANAPHASE_END) return cellR;
    if (frame < F_M_TELOPHASE_END) {
      return interpolate(frame, [F_M_ANAPHASE_END, F_M_TELOPHASE_END], [cellR, cellR + 40], {
        extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
      });
    }
    return cellR + 40;
  })();

  // Cleavage / pinch
  const pinchAmount = (() => {
    if (frame < F_M_TELOPHASE_END) return 0;
    return interpolate(frame, [F_M_TELOPHASE_END, F_M_CYTOKINESIS_END], [0, cellR + 40], {
      extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
    });
  })();

  // After cytokinesis show two daughters
  const showTwoDaughters = frame >= F_M_TELOPHASE_END;

  // Nuclear envelope opacity: present except mid-M-phase
  const envelopeOpacity = (() => {
    if (phase !== 'M') return 1;
    if (frame < F_M_PROPHASE_END) {
      // Fade out during prophase
      return interpolate(frame, [F_G2_END, F_M_PROPHASE_END], [1, 0], {
        extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
      });
    }
    if (frame < F_M_TELOPHASE_END) return 0;
    // Reform during telophase
    return interpolate(frame, [F_M_ANAPHASE_END, F_M_TELOPHASE_END], [0, 1], {
      extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
    });
  })();

  // Chromatin / chromosomes — different visual based on phase
  const chromatinState: ChromatinState = (() => {
    if (phase === 'G1') return 'diffuse-1n';
    if (phase === 'S') return 'diffuse-2n';
    if (phase === 'G2') return 'diffuse-2n';
    // M-phase
    if (frame < F_M_PROPHASE_END) return 'condensed';
    if (frame < F_M_METAPHASE_END) return 'aligned';
    if (frame < F_M_ANAPHASE_END) return 'separating';
    return 'separated';
  })();

  // Render the cell body
  const renderBody = () => {
    if (!showTwoDaughters || pinchAmount < 20) {
      return (
        <ellipse
          cx={STAGE_CX}
          cy={STAGE_CY}
          rx={cellRX}
          ry={cellR}
          fill={PAI_THEME.colors.coolWash}
          stroke={PAI_THEME.colors.accentLight}
          strokeWidth={5}
        />
      );
    }
    // Two daughter cells — circles whose centres separate as pinchAmount grows
    const offset = pinchAmount * 0.6;
    return (
      <>
        <ellipse
          cx={STAGE_CX - offset}
          cy={STAGE_CY}
          rx={cellR * 0.9}
          ry={cellR * 0.9}
          fill={PAI_THEME.colors.coolWash}
          stroke={PAI_THEME.colors.accentLight}
          strokeWidth={5}
        />
        <ellipse
          cx={STAGE_CX + offset}
          cy={STAGE_CY}
          rx={cellR * 0.9}
          ry={cellR * 0.9}
          fill={PAI_THEME.colors.coolWash}
          stroke={PAI_THEME.colors.accentLight}
          strokeWidth={5}
        />
      </>
    );
  };

  // Render nuclear envelope(s)
  const renderEnvelope = () => {
    if (!showTwoDaughters || pinchAmount < 20) {
      return (
        <circle
          cx={STAGE_CX}
          cy={STAGE_CY}
          r={cellR * 0.6}
          fill="none"
          stroke={PAI_THEME.colors.nuclearEnvelope}
          strokeWidth={4}
          opacity={envelopeOpacity}
          strokeDasharray={
            phase === 'M' && frame < F_M_PROPHASE_END ? '10 6' : undefined
          }
        />
      );
    }
    const offset = pinchAmount * 0.6;
    return (
      <>
        <circle
          cx={STAGE_CX - offset}
          cy={STAGE_CY}
          r={cellR * 0.5}
          fill="none"
          stroke={PAI_THEME.colors.nuclearEnvelope}
          strokeWidth={4}
          opacity={envelopeOpacity}
        />
        <circle
          cx={STAGE_CX + offset}
          cy={STAGE_CY}
          r={cellR * 0.5}
          fill="none"
          stroke={PAI_THEME.colors.nuclearEnvelope}
          strokeWidth={4}
          opacity={envelopeOpacity}
        />
      </>
    );
  };

  // Render chromatin / chromosomes
  const renderChromatin = () => {
    if (chromatinState === 'diffuse-1n') {
      // Wispy chromatin lines, single set (n unreplicated)
      return (
        <g
          stroke={PAI_THEME.colors.chromatid}
          strokeWidth={2}
          fill="none"
          opacity={0.55}
        >
          <path d={`M ${STAGE_CX - 70} ${STAGE_CY - 30} Q ${STAGE_CX - 30} ${STAGE_CY - 60} ${STAGE_CX + 30} ${STAGE_CY - 20}`} />
          <path d={`M ${STAGE_CX - 80} ${STAGE_CY + 10} Q ${STAGE_CX - 20} ${STAGE_CY + 40} ${STAGE_CX + 50} ${STAGE_CY + 0}`} />
          <path d={`M ${STAGE_CX - 50} ${STAGE_CY + 50} Q ${STAGE_CX + 10} ${STAGE_CY + 70} ${STAGE_CX + 70} ${STAGE_CY + 30}`} />
          <path d={`M ${STAGE_CX + 20} ${STAGE_CY - 60} Q ${STAGE_CX + 50} ${STAGE_CY - 30} ${STAGE_CX + 80} ${STAGE_CY - 50}`} />
        </g>
      );
    }
    if (chromatinState === 'diffuse-2n') {
      // Same wispy but denser (twice as much DNA)
      const sProgress = phase === 'S'
        ? interpolate(frame, [F_G1_END, F_S_END], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' })
        : 1;
      return (
        <>
          <g stroke={PAI_THEME.colors.chromatid} strokeWidth={2} fill="none" opacity={0.55}>
            <path d={`M ${STAGE_CX - 70} ${STAGE_CY - 30} Q ${STAGE_CX - 30} ${STAGE_CY - 60} ${STAGE_CX + 30} ${STAGE_CY - 20}`} />
            <path d={`M ${STAGE_CX - 80} ${STAGE_CY + 10} Q ${STAGE_CX - 20} ${STAGE_CY + 40} ${STAGE_CX + 50} ${STAGE_CY + 0}`} />
            <path d={`M ${STAGE_CX - 50} ${STAGE_CY + 50} Q ${STAGE_CX + 10} ${STAGE_CY + 70} ${STAGE_CX + 70} ${STAGE_CY + 30}`} />
            <path d={`M ${STAGE_CX + 20} ${STAGE_CY - 60} Q ${STAGE_CX + 50} ${STAGE_CY - 30} ${STAGE_CX + 80} ${STAGE_CY - 50}`} />
          </g>
          <g
            stroke={PAI_THEME.colors.chromatid}
            strokeWidth={2}
            fill="none"
            opacity={0.55 * sProgress}
            transform={`translate(8, 8)`}
          >
            <path d={`M ${STAGE_CX - 70} ${STAGE_CY - 30} Q ${STAGE_CX - 30} ${STAGE_CY - 60} ${STAGE_CX + 30} ${STAGE_CY - 20}`} />
            <path d={`M ${STAGE_CX - 80} ${STAGE_CY + 10} Q ${STAGE_CX - 20} ${STAGE_CY + 40} ${STAGE_CX + 50} ${STAGE_CY + 0}`} />
            <path d={`M ${STAGE_CX - 50} ${STAGE_CY + 50} Q ${STAGE_CX + 10} ${STAGE_CY + 70} ${STAGE_CX + 70} ${STAGE_CY + 30}`} />
            <path d={`M ${STAGE_CX + 20} ${STAGE_CY - 60} Q ${STAGE_CX + 50} ${STAGE_CY - 30} ${STAGE_CX + 80} ${STAGE_CY - 50}`} />
          </g>
        </>
      );
    }
    if (chromatinState === 'condensed') {
      // 4 chromosomes condensing into X shapes (sister chromatids visible)
      const t = interpolate(frame, [F_G2_END, F_M_PROPHASE_END], [0, 1], {
        extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
      });
      const armLen = 14 + 24 * t;  // grow more visible as condense
      const op = 0.4 + 0.6 * t;
      return (
        <g stroke={PAI_THEME.colors.chromatid} strokeWidth={5 + 3 * t} opacity={op} strokeLinecap="round">
          {/* Chromosome 1 — top-left */}
          <line x1={STAGE_CX - 60} y1={STAGE_CY - 60 - armLen / 2} x2={STAGE_CX - 60} y2={STAGE_CY - 60 + armLen / 2} />
          <line x1={STAGE_CX - 60 - armLen / 2} y1={STAGE_CY - 60} x2={STAGE_CX - 60 + armLen / 2} y2={STAGE_CY - 60} />
          {/* Chromosome 2 — top-right */}
          <line x1={STAGE_CX + 50} y1={STAGE_CY - 50 - armLen / 2} x2={STAGE_CX + 50} y2={STAGE_CY - 50 + armLen / 2} />
          <line x1={STAGE_CX + 50 - armLen / 2} y1={STAGE_CY - 50} x2={STAGE_CX + 50 + armLen / 2} y2={STAGE_CY - 50} />
          {/* Chromosome 3 — bottom-left */}
          <line x1={STAGE_CX - 50} y1={STAGE_CY + 50 - armLen / 2} x2={STAGE_CX - 50} y2={STAGE_CY + 50 + armLen / 2} />
          <line x1={STAGE_CX - 50 - armLen / 2} y1={STAGE_CY + 50} x2={STAGE_CX - 50 + armLen / 2} y2={STAGE_CY + 50} />
          {/* Chromosome 4 — bottom-right */}
          <line x1={STAGE_CX + 60} y1={STAGE_CY + 60 - armLen / 2} x2={STAGE_CX + 60} y2={STAGE_CY + 60 + armLen / 2} />
          <line x1={STAGE_CX + 60 - armLen / 2} y1={STAGE_CY + 60} x2={STAGE_CX + 60 + armLen / 2} y2={STAGE_CY + 60} />
        </g>
      );
    }
    if (chromatinState === 'aligned') {
      // 4 X-shaped chromosomes lined up vertically along centre
      const t = interpolate(frame, [F_M_PROPHASE_END, F_M_METAPHASE_END], [0, 1], {
        extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
      });
      const armLen = 38;
      // From scattered → metaphase plate
      const targets = [
        { x0: STAGE_CX - 60, y0: STAGE_CY - 60, x1: STAGE_CX, y1: STAGE_CY - 90 },
        { x0: STAGE_CX + 50, y0: STAGE_CY - 50, x1: STAGE_CX, y1: STAGE_CY - 30 },
        { x0: STAGE_CX - 50, y0: STAGE_CY + 50, x1: STAGE_CX, y1: STAGE_CY + 30 },
        { x0: STAGE_CX + 60, y0: STAGE_CY + 60, x1: STAGE_CX, y1: STAGE_CY + 90 },
      ];
      return (
        <>
          {/* Spindle from poles */}
          <g stroke={PAI_THEME.colors.spindle} strokeWidth={2}>
            {targets.map((tg, i) => {
              const x = tg.x0 + (tg.x1 - tg.x0) * t;
              const y = tg.y0 + (tg.y1 - tg.y0) * t;
              return (
                <g key={i}>
                  <line x1={STAGE_CX - 250} y1={STAGE_CY} x2={x} y2={y} />
                  <line x1={STAGE_CX + 250} y1={STAGE_CY} x2={x} y2={y} />
                </g>
              );
            })}
          </g>
          {/* Metaphase plate */}
          <line
            x1={STAGE_CX} y1={STAGE_CY - 130}
            x2={STAGE_CX} y2={STAGE_CY + 130}
            stroke={PAI_THEME.colors.textMuted}
            strokeWidth={2}
            strokeDasharray="6 4"
            opacity={t}
          />
          {/* Chromosomes (X shapes moving from prior position to plate) */}
          <g stroke={PAI_THEME.colors.chromatid} strokeWidth={8} strokeLinecap="round">
            {targets.map((tg, i) => {
              const x = tg.x0 + (tg.x1 - tg.x0) * t;
              const y = tg.y0 + (tg.y1 - tg.y0) * t;
              return (
                <g key={i}>
                  <line x1={x} y1={y - armLen / 2} x2={x} y2={y + armLen / 2} />
                  <line x1={x - armLen / 2} y1={y} x2={x + armLen / 2} y2={y} />
                </g>
              );
            })}
          </g>
          {/* Pole markers */}
          <g fill={PAI_THEME.colors.centrosome}>
            <rect x={STAGE_CX - 254} y={STAGE_CY - 6} width={10} height={12} rx={2} />
            <rect x={STAGE_CX + 244} y={STAGE_CY - 6} width={10} height={12} rx={2} />
          </g>
        </>
      );
    }
    if (chromatinState === 'separating') {
      // Sister chromatids separating — half going left, half going right
      const t = interpolate(frame, [F_M_METAPHASE_END, F_M_ANAPHASE_END], [0, 1], {
        extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
      });
      const offset = t * 160;  // px from centre
      const armLen = 38;
      const yPositions = [STAGE_CY - 90, STAGE_CY - 30, STAGE_CY + 30, STAGE_CY + 90];
      return (
        <>
          {/* Spindle (shortening as anaphase progresses) */}
          <g stroke={PAI_THEME.colors.spindle} strokeWidth={2}>
            {yPositions.map((y, i) => (
              <g key={i}>
                <line x1={STAGE_CX - 250} y1={STAGE_CY} x2={STAGE_CX - offset} y2={y} />
                <line x1={STAGE_CX + 250} y1={STAGE_CY} x2={STAGE_CX + offset} y2={y} />
              </g>
            ))}
          </g>
          {/* Two halves */}
          <g stroke={PAI_THEME.colors.chromatid} strokeWidth={6} strokeLinecap="round">
            {yPositions.map((y, i) => (
              <g key={i}>
                {/* Left chromatid (single line) */}
                <line x1={STAGE_CX - offset - 6} y1={y - armLen / 3} x2={STAGE_CX - offset - 6} y2={y + armLen / 3} />
                {/* Right chromatid */}
                <line x1={STAGE_CX + offset + 6} y1={y - armLen / 3} x2={STAGE_CX + offset + 6} y2={y + armLen / 3} />
              </g>
            ))}
          </g>
          {/* Pole markers */}
          <g fill={PAI_THEME.colors.centrosome}>
            <rect x={STAGE_CX - 254} y={STAGE_CY - 6} width={10} height={12} rx={2} />
            <rect x={STAGE_CX + 244} y={STAGE_CY - 6} width={10} height={12} rx={2} />
          </g>
        </>
      );
    }
    // separated: chromosomes clustered at each pole, decondensing
    {
      const t = interpolate(frame, [F_M_ANAPHASE_END, F_M_TELOPHASE_END], [0, 1], {
        extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
      });
      const armLen = 38 - 24 * t;
      const op = 1 - 0.5 * t;
      const offsetBase = 160;
      const yPositions = [STAGE_CY - 90, STAGE_CY - 30, STAGE_CY + 30, STAGE_CY + 90];

      // After cytokinesis splits the cells, the offset becomes the daughter centre offset
      const finalOffset = pinchAmount * 0.6 + offsetBase;

      return (
        <g stroke={PAI_THEME.colors.chromatid} strokeWidth={5} strokeLinecap="round" opacity={op}>
          {yPositions.map((y, i) => (
            <g key={i}>
              <line
                x1={STAGE_CX - finalOffset - 6}
                y1={y - armLen / 3}
                x2={STAGE_CX - finalOffset - 6}
                y2={y + armLen / 3}
              />
              <line
                x1={STAGE_CX + finalOffset + 6}
                y1={y - armLen / 3}
                x2={STAGE_CX + finalOffset + 6}
                y2={y + armLen / 3}
              />
            </g>
          ))}
        </g>
      );
    }
  };

  return (
    <g>
      {renderBody()}
      {renderEnvelope()}
      {renderChromatin()}
    </g>
  );
};

// ── Main scene ───────────────────────────────────────────────────────────────
export const CellCycleWheelScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const titleSpring = spring({ frame, fps, config: PAI_THEME.animation.springDefault });
  const titleOp = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: 'clamp' });
  const subOp   = interpolate(frame, [20, 60], [0, 1], { extrapolateRight: 'clamp' });

  const activePhase = getActivePhase(frame);
  const activeWedge = WEDGES.find(w => w.key === activePhase)!;

  // Sweep hand angle
  const handAngle = cycleProgress(frame) * Math.PI * 2;

  // Closing caption
  const captionOp = interpolate(
    frame,
    [F_CAPTION_START, F_CAPTION_END],
    [0, 1],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
  );

  return (
    <AbsoluteFill style={{
      background: `linear-gradient(135deg, ${PAI_THEME.colors.background}, ${PAI_THEME.colors.backgroundAlt})`,
      fontFamily: PAI_THEME.typography.fontFamily,
    }}>
      {/* ── Title ────────────────────────────────────────────── */}
      <div style={{
        position: 'absolute', top: 30, left: 0, right: 0, textAlign: 'center',
      }}>
        <h1 style={{
          fontSize: 56, color: PAI_THEME.colors.text, margin: 0,
          opacity: titleOp, transform: `scale(${titleSpring})`,
        }}>
          The Cell Cycle — One Round of a Cell&apos;s Life
        </h1>
        <p style={{
          fontSize: 26, color: PAI_THEME.colors.accentLight, marginTop: 6, fontStyle: 'italic',
          opacity: subOp,
        }}>
          G₁ → S → G₂ → M, then divide. Watch what happens at each phase.
        </p>
      </div>

      {/* ── SVG layer ────────────────────────────────────────── */}
      <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} style={{ position: 'absolute', inset: 0 }}>
        {/* ── Cell-cycle wheel ───────────────────────────────── */}
        {/* Faint outer ring */}
        <circle
          cx={WHEEL_CX}
          cy={WHEEL_CY}
          r={WHEEL_R + 24}
          fill="none"
          stroke={PAI_THEME.colors.textDark}
          strokeWidth={2}
          strokeDasharray="6 8"
          opacity={0.4}
        />

        {/* Wedges */}
        {WEDGES.map((w) => {
          const isActive = w.key === activePhase;
          const op = isActive ? 0.9 : 0.32;
          return (
            <g key={w.key}>
              <path
                d={wedgePath(WHEEL_CX, WHEEL_CY, WHEEL_R, 100, w.startAngle, w.endAngle)}
                fill={w.color}
                opacity={op}
                stroke={w.color}
                strokeWidth={isActive ? 5 : 2}
              />
              {/* Wedge label — placed at midpoint of arc, offset outward */}
              {(() => {
                const mid = (w.startAngle + w.endAngle) / 2;
                const lp = polar(WHEEL_CX, WHEEL_CY, (WHEEL_R + 100) / 2, mid);
                const sp = polar(WHEEL_CX, WHEEL_CY, (WHEEL_R + 100) / 2 + 32, mid);
                return (
                  <g>
                    <text
                      x={lp.x}
                      y={lp.y - 6}
                      fill={PAI_THEME.colors.text}
                      fontSize={isActive ? 44 : 32}
                      fontWeight={700}
                      textAnchor="middle"
                    >
                      {w.key === 'G1' ? 'G₁' : w.key === 'G2' ? 'G₂' : w.key}
                    </text>
                    <text
                      x={sp.x}
                      y={sp.y + 18}
                      fill={PAI_THEME.colors.textMuted}
                      fontSize={18}
                      textAnchor="middle"
                    >
                      {w.duration}
                    </text>
                  </g>
                );
              })()}
            </g>
          );
        })}

        {/* Inner hub */}
        <circle
          cx={WHEEL_CX}
          cy={WHEEL_CY}
          r={92}
          fill={PAI_THEME.colors.background}
          stroke={PAI_THEME.colors.textMuted}
          strokeWidth={2}
        />
        <text
          x={WHEEL_CX}
          y={WHEEL_CY - 12}
          fill={PAI_THEME.colors.textMuted}
          fontSize={20}
          textAnchor="middle"
        >
          Active phase
        </text>
        <text
          x={WHEEL_CX}
          y={WHEEL_CY + 22}
          fill={activeWedge.color}
          fontSize={48}
          fontWeight={700}
          textAnchor="middle"
        >
          {activePhase === 'G1' ? 'G₁' : activePhase === 'G2' ? 'G₂' : activePhase}
        </text>
        <text
          x={WHEEL_CX}
          y={WHEEL_CY + 52}
          fill={PAI_THEME.colors.textMuted}
          fontSize={14}
          textAnchor="middle"
        >
          {activeWedge.duration}
        </text>

        {/* Sweep hand */}
        {(() => {
          const hp = polar(WHEEL_CX, WHEEL_CY, WHEEL_R - 8, handAngle);
          return (
            <g>
              <line
                x1={WHEEL_CX}
                y1={WHEEL_CY}
                x2={hp.x}
                y2={hp.y}
                stroke={PAI_THEME.colors.text}
                strokeWidth={5}
                strokeLinecap="round"
              />
              <circle cx={hp.x} cy={hp.y} r={10} fill={activeWedge.color} stroke={PAI_THEME.colors.text} strokeWidth={3} />
            </g>
          );
        })()}

        {/* Checkpoint stars at G1/S, G2/M, and inside M */}
        {(() => {
          const stars = [
            { angle: HRS.G1 * ANG_PER_HR, label: 'G₁/S' },
            { angle: (HRS.G1 + HRS.S + HRS.G2) * ANG_PER_HR, label: 'G₂/M' },
          ];
          return stars.map((s, i) => {
            const p = polar(WHEEL_CX, WHEEL_CY, WHEEL_R + 4, s.angle);
            return (
              <g key={i} transform={`translate(${p.x}, ${p.y})`}>
                <polygon
                  points="0,-12 4,-3 14,-3 6,3 9,12 0,7 -9,12 -6,3 -14,-3 -4,-3"
                  fill={PAI_THEME.colors.checkpoint}
                  stroke={PAI_THEME.colors.fungi}
                  strokeWidth={1.5}
                />
                <text x={0} y={-22} fontSize={16} fontWeight={700} fill={PAI_THEME.colors.checkpoint} textAnchor="middle">
                  {s.label}
                </text>
              </g>
            );
          });
        })()}

        {/* ── Stage caption ───────────────────────────────────── */}
        <text
          x={STAGE_CX}
          y={170}
          fill={activeWedge.color}
          fontSize={42}
          fontWeight={700}
          textAnchor="middle"
        >
          {activeWedge.label}
        </text>
        <text
          x={STAGE_CX}
          y={206}
          fill={PAI_THEME.colors.textMuted}
          fontSize={22}
          textAnchor="middle"
        >
          {activeWedge.hint}
        </text>

        {/* ── Stage viewport ──────────────────────────────────── */}
        <circle
          cx={STAGE_CX}
          cy={STAGE_CY}
          r={STAGE_R}
          fill={PAI_THEME.colors.backgroundDark}
          stroke={activeWedge.color}
          strokeWidth={6}
        />

        <defs>
          <clipPath id="cellCycleStageClip">
            <circle cx={STAGE_CX} cy={STAGE_CY} r={STAGE_R - 4} />
          </clipPath>
        </defs>

        <g clipPath="url(#cellCycleStageClip)">
          <StageCell frame={frame} />
        </g>

        {/* M-phase sub-stage label */}
        {activePhase === 'M' && (() => {
          let label = 'Prophase — chromosomes condense';
          if (frame >= F_M_PROPHASE_END && frame < F_M_METAPHASE_END) label = 'Metaphase — line up at the equator';
          else if (frame >= F_M_METAPHASE_END && frame < F_M_ANAPHASE_END) label = 'Anaphase — sisters separate';
          else if (frame >= F_M_ANAPHASE_END && frame < F_M_TELOPHASE_END) label = 'Telophase — envelopes reform';
          else if (frame >= F_M_TELOPHASE_END) label = 'Cytokinesis — pinch into two cells';
          return (
            <text
              x={STAGE_CX}
              y={STAGE_CY + STAGE_R + 36}
              fill={PAI_THEME.colors.text}
              fontSize={24}
              fontWeight={700}
              textAnchor="middle"
            >
              {label}
            </text>
          );
        })()}

        {/* DNA content readout (small, lower-left) */}
        <g transform={`translate(120, 980)`}>
          <text fill={PAI_THEME.colors.textMuted} fontSize={20} fontWeight={700}>
            DNA content:
            {' '}
            {activePhase === 'G1' && '2C'}
            {activePhase === 'S' && '2C → 4C (replicating)'}
            {activePhase === 'G2' && '4C'}
            {activePhase === 'M' && '4C → 2C per daughter'}
          </text>
        </g>
      </svg>

      {/* ── Closing caption ──────────────────────────────────── */}
      <div style={{
        position: 'absolute', bottom: 32, left: 0, right: 0, textAlign: 'center',
        fontSize: 30, fontWeight: 700,
        color: PAI_THEME.colors.text,
        opacity: captionOp,
      }}>
        One round, two daughter cells, identical genomes — now they each start their own G₁.
      </div>
    </AbsoluteFill>
  );
};
