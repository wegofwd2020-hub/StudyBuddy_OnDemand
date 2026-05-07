/**
 * ElectronFillScene — Aufbau electron-filling animation from H (Z=1) to Ar (Z=18).
 *
 * Eighteen orbital "slots" (each spin-up + spin-down position in an orbital
 * box) fill one at a time, every 30 frames. Order honours Aufbau (1s → 2s →
 * 2p → 3s → 3p) and Hund's rule (parallel spins before pairing within p).
 *
 * Layout:
 *   Title at top
 *   Row of 9 orbital boxes: 1s | 2s | 2pₓ | 2p_y | 2p_z | 3s | 3pₓ | 3p_y | 3p_z
 *   Configuration string under the boxes (builds up)
 *   Element name on the right (updates: H, He, Li, ..., Ar)
 *
 * Frames @ 30fps (24 s total = 720 frames):
 *   0–60     title fade
 *   60–120   orbital boxes appear
 *   120–660  18 electrons fill in (1 every 30 frames, 18 s of action)
 *   660–720  hold final configuration (Argon)
 */
import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate, useVideoConfig, spring } from 'remotion';
import { PAI_THEME } from '../theme';

// ── Orbital box layout ──────────────────────────────────────────────────────
const BOX_W = 100;
const BOX_H = 110;
const BOX_GAP = 28;
const BOX_ROW_Y = 360;

const ORBITALS = [
  { id: '1s',   label: '1s',   x: 0 },
  { id: '2s',   label: '2s',   x: 1 },
  { id: '2px',  label: '2pₓ',  x: 2 },
  { id: '2py',  label: '2p_y', x: 3 },
  { id: '2pz',  label: '2p_z', x: 4 },
  { id: '3s',   label: '3s',   x: 5 },
  { id: '3px',  label: '3pₓ',  x: 6 },
  { id: '3py',  label: '3p_y', x: 7 },
  { id: '3pz',  label: '3p_z', x: 8 },
];

const TOTAL_W = ORBITALS.length * BOX_W + (ORBITALS.length - 1) * BOX_GAP;
const ROW_X0 = (1920 - TOTAL_W) / 2;

const orbitalX = (i: number) => ROW_X0 + i * (BOX_W + BOX_GAP);

// ── Aufbau fill order (orbital id + spin) ───────────────────────────────────
type Spin = 'up' | 'down';
const FILL_ORDER: Array<{ orbital: string; spin: Spin }> = [
  { orbital: '1s',  spin: 'up' },     // H  (Z=1)
  { orbital: '1s',  spin: 'down' },   // He (Z=2)
  { orbital: '2s',  spin: 'up' },     // Li
  { orbital: '2s',  spin: 'down' },   // Be
  // Hund: spread before pairing in 2p
  { orbital: '2px', spin: 'up' },     // B
  { orbital: '2py', spin: 'up' },     // C
  { orbital: '2pz', spin: 'up' },     // N  (half-filled p)
  { orbital: '2px', spin: 'down' },   // O  (pairing begins)
  { orbital: '2py', spin: 'down' },   // F
  { orbital: '2pz', spin: 'down' },   // Ne (full p)
  { orbital: '3s',  spin: 'up' },     // Na
  { orbital: '3s',  spin: 'down' },   // Mg
  // Hund: spread in 3p
  { orbital: '3px', spin: 'up' },     // Al
  { orbital: '3py', spin: 'up' },     // Si
  { orbital: '3pz', spin: 'up' },     // P
  { orbital: '3px', spin: 'down' },   // S
  { orbital: '3py', spin: 'down' },   // Cl
  { orbital: '3pz', spin: 'down' },   // Ar
];

const ELEMENTS = [
  '', 'H', 'He', 'Li', 'Be', 'B', 'C', 'N', 'O', 'F', 'Ne',
  'Na', 'Mg', 'Al', 'Si', 'P', 'S', 'Cl', 'Ar',
];

const ELEMENT_NAMES = [
  '', 'Hydrogen', 'Helium', 'Lithium', 'Beryllium', 'Boron', 'Carbon',
  'Nitrogen', 'Oxygen', 'Fluorine', 'Neon',
  'Sodium', 'Magnesium', 'Aluminium', 'Silicon', 'Phosphorus',
  'Sulfur', 'Chlorine', 'Argon',
];

// ── Configuration string builder ────────────────────────────────────────────
function buildConfig(electronCount: number): string {
  const counts: Record<string, number> = {};
  for (let i = 0; i < Math.min(electronCount, FILL_ORDER.length); i++) {
    const o = FILL_ORDER[i].orbital;
    counts[o] = (counts[o] ?? 0) + 1;
  }
  const parts: string[] = [];
  // Group p subshells back into a single subshell exponent (Aufbau by subshell)
  const subshellOrder = ['1s', '2s', '2p', '3s', '3p'];
  const subshellCounts: Record<string, number> = {};
  for (const [orb, c] of Object.entries(counts)) {
    const subshell = orb.replace(/[xyz]$/, '').slice(0, 2); // "2px" → "2p"
    subshellCounts[subshell] = (subshellCounts[subshell] ?? 0) + c;
  }
  for (const ss of subshellOrder) {
    if (subshellCounts[ss]) {
      parts.push(`${ss}${superscript(subshellCounts[ss])}`);
    }
  }
  return parts.join(' ');
}

function superscript(n: number): string {
  const map: Record<string, string> = { '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴', '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹' };
  return String(n).split('').map((c) => map[c] ?? c).join('');
}

// ── Frame anchors ───────────────────────────────────────────────────────────
const F_TITLE_END = 60;
const F_BOXES_IN = 120;
const F_FILL_START = 120;
const FRAMES_PER_ELECTRON = 30;
const F_FILL_END = F_FILL_START + FILL_ORDER.length * FRAMES_PER_ELECTRON; // 660

export const ElectronFillScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const titleScale = spring({ frame, fps, config: PAI_THEME.animation.springDefault });
  const titleOp = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: 'clamp' });
  const subOp = interpolate(frame, [20, 60], [0, 1], { extrapolateRight: 'clamp' });
  const boxesOp = interpolate(frame, [60, F_BOXES_IN], [0, 1], { extrapolateRight: 'clamp' });

  // How many electrons have arrived
  const filledCount = Math.max(0, Math.min(FILL_ORDER.length, Math.floor((frame - F_FILL_START) / FRAMES_PER_ELECTRON)));

  // Per-orbital spin lists (from FILL_ORDER, sliced to filledCount)
  const spinsByOrbital: Record<string, Spin[]> = {};
  for (const o of ORBITALS) spinsByOrbital[o.id] = [];
  for (let i = 0; i < filledCount; i++) {
    const f = FILL_ORDER[i];
    spinsByOrbital[f.orbital].push(f.spin);
  }

  // Fade-in for the most-recently-arrived electron (the one currently filling)
  const inProgressIdx = filledCount; // the next one
  const inProgressFrame = frame - (F_FILL_START + inProgressIdx * FRAMES_PER_ELECTRON);
  const inProgressOp = inProgressIdx < FILL_ORDER.length
    ? interpolate(inProgressFrame, [0, FRAMES_PER_ELECTRON / 2], [0, 1], { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' })
    : 1;

  const config = buildConfig(filledCount);
  const elementSymbol = filledCount > 0 && filledCount <= 18 ? ELEMENTS[filledCount] : '';
  const elementName = filledCount > 0 && filledCount <= 18 ? ELEMENT_NAMES[filledCount] : '';

  return (
    <AbsoluteFill style={{
      background: `linear-gradient(135deg, ${PAI_THEME.colors.background}, ${PAI_THEME.colors.backgroundAlt})`,
      fontFamily: PAI_THEME.typography.fontFamily,
    }}>
      {/* Title */}
      <div style={{ position: 'absolute', top: 30, left: 0, right: 0, textAlign: 'center' }}>
        <h1 style={{
          fontSize: 56, color: PAI_THEME.colors.text, margin: 0,
          opacity: titleOp, transform: `scale(${titleScale})`,
        }}>
          Aufbau Filling — Hydrogen through Argon
        </h1>
        <p style={{
          fontSize: 26, color: PAI_THEME.colors.accentLight, marginTop: 6, fontStyle: 'italic',
          opacity: subOp,
        }}>
          1s → 2s → 2p → 3s → 3p   ·   Hund's rule: spread before pairing   ·   Pauli: opposite spins per orbital
        </p>
      </div>

      <svg width={1920} height={1080} viewBox="0 0 1920 1080" style={{ position: 'absolute', inset: 0, opacity: boxesOp }}>
        {/* Subshell group brackets */}
        <SubshellBracket label="1s"  startIdx={0} endIdx={0} />
        <SubshellBracket label="2s"  startIdx={1} endIdx={1} />
        <SubshellBracket label="2p"  startIdx={2} endIdx={4} />
        <SubshellBracket label="3s"  startIdx={5} endIdx={5} />
        <SubshellBracket label="3p"  startIdx={6} endIdx={8} />

        {/* Orbital boxes */}
        {ORBITALS.map((o) => {
          const x = orbitalX(o.x);
          const spins = spinsByOrbital[o.id];
          return (
            <g key={o.id}>
              <rect x={x} y={BOX_ROW_Y} width={BOX_W} height={BOX_H}
                rx={10}
                fill={PAI_THEME.colors.backgroundAlt}
                stroke={PAI_THEME.colors.accent} strokeWidth={2.5} />
              <text x={x + BOX_W / 2} y={BOX_ROW_Y + BOX_H + 36}
                fill={PAI_THEME.colors.text} fontSize={26} fontWeight={700} textAnchor="middle">
                {o.label}
              </text>

              {/* Spin arrows */}
              {spins.includes('up') && (
                <SpinArrow
                  x={x + BOX_W * 0.32}
                  yTop={BOX_ROW_Y + 18}
                  yBot={BOX_ROW_Y + BOX_H - 18}
                  spin="up"
                  opacity={
                    inProgressIdx < FILL_ORDER.length &&
                    FILL_ORDER[inProgressIdx - 1]?.orbital === o.id &&
                    FILL_ORDER[inProgressIdx - 1]?.spin === 'up'
                      ? 1
                      : 1
                  }
                />
              )}
              {spins.includes('down') && (
                <SpinArrow
                  x={x + BOX_W * 0.68}
                  yTop={BOX_ROW_Y + 18}
                  yBot={BOX_ROW_Y + BOX_H - 18}
                  spin="down"
                  opacity={1}
                />
              )}

              {/* In-progress arrow being added (fades in) */}
              {inProgressIdx > 0
                && inProgressIdx <= FILL_ORDER.length
                && FILL_ORDER[inProgressIdx - 1]?.orbital === o.id
                && (
                  // Don't double-render — already in spins[]; the opacity logic above doesn't fade because spins is already inclusive.
                  // We render the in-progress arrow explicitly below for fade-in by suppressing the included copy.
                  <></>
                )}
            </g>
          );
        })}

        {/* In-progress fade-in: render only the most-recent arrow with opacity */}
        {filledCount > 0 && filledCount <= FILL_ORDER.length && (() => {
          const last = FILL_ORDER[filledCount - 1];
          const orb = ORBITALS.find((o) => o.id === last.orbital);
          if (!orb) return null;
          const x = orbitalX(orb.x);
          const aliveFrames = frame - (F_FILL_START + (filledCount - 1) * FRAMES_PER_ELECTRON);
          if (aliveFrames > FRAMES_PER_ELECTRON / 2) return null; // already steady-state
          const fadeIn = interpolate(aliveFrames, [0, FRAMES_PER_ELECTRON / 2], [0, 1], { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' });
          // Mask the steady-state arrow under the fade-in by re-drawing background-coloured rect at that arrow position is overkill — instead just lay the arrow on top with the fade alpha.
          return (
            <g key="in-progress" opacity={fadeIn}>
              <SpinArrow
                x={x + BOX_W * (last.spin === 'up' ? 0.32 : 0.68)}
                yTop={BOX_ROW_Y + 18}
                yBot={BOX_ROW_Y + BOX_H - 18}
                spin={last.spin}
                glow
                opacity={1}
              />
            </g>
          );
        })()}
      </svg>

      {/* Configuration string */}
      <div style={{
        position: 'absolute', top: 620, left: 0, right: 0, textAlign: 'center',
        opacity: boxesOp,
      }}>
        <div style={{
          fontSize: 24, color: PAI_THEME.colors.textMuted, marginBottom: 4,
        }}>
          electron configuration
        </div>
        <div style={{
          fontSize: 56, color: PAI_THEME.colors.accentLight, fontWeight: 700,
          letterSpacing: 1,
        }}>
          {config || '(empty)'}
        </div>
      </div>

      {/* Element name (right side, large) */}
      <div style={{
        position: 'absolute', top: 760, left: 0, right: 0, textAlign: 'center',
        opacity: boxesOp,
      }}>
        <div style={{
          fontSize: 22, color: PAI_THEME.colors.textMuted,
        }}>
          atom built so far
        </div>
        <div style={{
          fontSize: 80, color: PAI_THEME.colors.text, fontWeight: 700, lineHeight: 1.1,
        }}>
          {elementSymbol || '—'}
        </div>
        <div style={{
          fontSize: 28, color: PAI_THEME.colors.warning, fontWeight: 600,
        }}>
          {elementName} {filledCount > 0 ? `· Z = ${filledCount}` : ''}
        </div>
      </div>

      {/* Bottom strapline */}
      <div style={{
        position: 'absolute', top: 1010, left: 0, right: 0, textAlign: 'center',
        fontSize: 22, color: PAI_THEME.colors.textMuted,
      }}>
        Each tick adds one electron.   Watch 2p and 3p: three parallel up-arrows appear before any pairs (Hund's rule in action).
      </div>
    </AbsoluteFill>
  );
};

// ── Sub-components ──────────────────────────────────────────────────────────

const SpinArrow: React.FC<{
  x: number;
  yTop: number;
  yBot: number;
  spin: Spin;
  opacity?: number;
  glow?: boolean;
}> = ({ x, yTop, yBot, spin, opacity = 1, glow = false }) => {
  const color = spin === 'up' ? PAI_THEME.colors.electron : PAI_THEME.colors.warning;
  const head = 12;
  if (spin === 'up') {
    return (
      <g opacity={opacity}>
        <line x1={x} y1={yBot} x2={x} y2={yTop + head}
          stroke={color} strokeWidth={4}
          style={glow ? { filter: `drop-shadow(0 0 8px ${color})` } : undefined} />
        <polygon points={`${x - 7},${yTop + head} ${x + 7},${yTop + head} ${x},${yTop}`}
          fill={color} />
      </g>
    );
  }
  return (
    <g opacity={opacity}>
      <line x1={x} y1={yTop} x2={x} y2={yBot - head}
        stroke={color} strokeWidth={4}
        style={glow ? { filter: `drop-shadow(0 0 8px ${color})` } : undefined} />
      <polygon points={`${x - 7},${yBot - head} ${x + 7},${yBot - head} ${x},${yBot}`}
        fill={color} />
    </g>
  );
};

const SubshellBracket: React.FC<{ label: string; startIdx: number; endIdx: number }> = ({ label, startIdx, endIdx }) => {
  const x1 = orbitalX(startIdx);
  const x2 = orbitalX(endIdx) + BOX_W;
  const y = BOX_ROW_Y - 28;
  return (
    <g>
      <line x1={x1} y1={y} x2={x2} y2={y}
        stroke={PAI_THEME.colors.accent} strokeWidth={2} />
      <line x1={x1} y1={y} x2={x1} y2={y + 8}
        stroke={PAI_THEME.colors.accent} strokeWidth={2} />
      <line x1={x2} y1={y} x2={x2} y2={y + 8}
        stroke={PAI_THEME.colors.accent} strokeWidth={2} />
      <text x={(x1 + x2) / 2} y={y - 8}
        fill={PAI_THEME.colors.accent} fontSize={24} fontWeight={700} textAnchor="middle">
        {label}
      </text>
    </g>
  );
};
