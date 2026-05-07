/**
 * BohrTransitionScene — Bohr-model atom showing an n=3 → n=2 electron drop
 * emitting a photon, which travels to a hydrogen-spectrum strip and lights
 * up the H-α line (656.3 nm, red).
 *
 * Layout:
 *   - Atom on the left (Bohr shells n=1, 2, 3)
 *   - Energy ladder + spectrum strip on the right
 *   - Title at top, caption at bottom
 *
 * Frames @ 30fps (24 s total = 720 frames):
 *   0–60     title + subtitle fade in
 *   60–150   atom appears, electron orbits in n=3
 *   150–300  pre-transition orbit (5 s)
 *   300–420  electron drops from n=3 to n=2 (radial interpolation)
 *   420–540  photon flies from atom to spectrum strip
 *   540–720  H-α line lights up; caption fades in
 */
import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate, useVideoConfig, spring } from 'remotion';
import { PAI_THEME } from '../theme';

// ── Geometry ─────────────────────────────────────────────────────────────────
const ATOM_CX = 540;
const ATOM_CY = 580;
const SHELL_R = [120, 220, 340];   // n = 1, 2, 3 radii
const NUCLEUS_R = 36;
const ELECTRON_R = 16;

// Spectrum strip on the right
const SPEC_X = 1100;
const SPEC_W = 720;
const SPEC_Y = 800;
const SPEC_H = 80;
// Wavelength range 380–700 nm; H-α is at 656.3 nm
const NM_MIN = 380, NM_MAX = 700;
const HALPHA_NM = 656.3;
const halphaPx = SPEC_X + ((HALPHA_NM - NM_MIN) / (NM_MAX - NM_MIN)) * SPEC_W;

// Energy ladder
const LADDER_X = 1180;
const LADDER_TOP = 220;
const LADDER_BOTTOM = 580;
const LADDER_WIDTH = 80;
// n=1 at bottom (ground state, lowest energy), n=3 at top
const ladderY = (n: number) => LADDER_BOTTOM - ((n - 1) / 2) * (LADDER_BOTTOM - LADDER_TOP);

// ── Frame anchors ────────────────────────────────────────────────────────────
const F_TITLE_END = 60;
const F_SUB_END = 150;
const F_PRE_END = 300;
const F_DROP_END = 420;
const F_PHOTON_END = 540;
const F_LINE_LIT = 600;

export const BohrTransitionScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const titleScale = spring({ frame, fps, config: PAI_THEME.animation.springDefault });
  const titleOp = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: 'clamp' });
  const subOp = interpolate(frame, [20, 60], [0, 1], { extrapolateRight: 'clamp' });
  const atomOp = interpolate(frame, [60, F_SUB_END], [0, 1], { extrapolateRight: 'clamp' });

  // ── Electron position ────────────────────────────────────────────────────
  // Phase 1 (orbit n=3): θ = (frame-60)/30 rad/s, on shell radius SHELL_R[2]
  // Phase 2 (drop n=3 → n=2): radius interpolates SHELL_R[2] → SHELL_R[1]
  // Phase 3 (orbit n=2): on shell radius SHELL_R[1]
  const orbitFrame = Math.max(0, frame - 60);
  const theta = orbitFrame * 0.04; // ~1.2 rad/s, slow enough to follow

  let electronR: number;
  if (frame < F_PRE_END) {
    electronR = SHELL_R[2];
  } else if (frame < F_DROP_END) {
    const k = (frame - F_PRE_END) / (F_DROP_END - F_PRE_END);
    electronR = SHELL_R[2] + (SHELL_R[1] - SHELL_R[2]) * k;
  } else {
    electronR = SHELL_R[1];
  }
  const electronX = ATOM_CX + electronR * Math.cos(theta);
  const electronY = ATOM_CY + electronR * Math.sin(theta);

  // ── Photon emission ──────────────────────────────────────────────────────
  // Photon emitted at the start of the drop, travels from atom centre to spectrum line.
  const photonStartFrame = F_PRE_END;
  const photonEndFrame = F_PHOTON_END;
  const photonProgress = interpolate(
    frame, [photonStartFrame, photonEndFrame], [0, 1],
    { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' },
  );
  const photonX = ATOM_CX + (halphaPx - ATOM_CX) * photonProgress;
  const photonY = ATOM_CY + (SPEC_Y + SPEC_H / 2 - ATOM_CY) * photonProgress;
  const photonVisible = frame >= photonStartFrame && frame <= photonEndFrame;

  // ── H-α line brightness ──────────────────────────────────────────────────
  const lineBrightness = interpolate(
    frame, [F_PHOTON_END - 10, F_LINE_LIT], [0.18, 1],
    { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' },
  );
  const lineGlow = interpolate(
    frame, [F_PHOTON_END - 10, F_LINE_LIT, F_LINE_LIT + 30], [0, 14, 8],
    { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' },
  );

  // Energy-ladder transition arrow (highlighted during drop)
  const transitionArrowOp = interpolate(
    frame, [F_PRE_END - 30, F_PRE_END, F_DROP_END, F_DROP_END + 60], [0, 1, 1, 0.5],
    { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' },
  );

  // Final caption
  const captionOp = interpolate(frame, [F_LINE_LIT, F_LINE_LIT + 60], [0, 1], { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' });

  return (
    <AbsoluteFill style={{
      background: `linear-gradient(135deg, ${PAI_THEME.colors.background}, ${PAI_THEME.colors.backgroundAlt})`,
      fontFamily: PAI_THEME.typography.fontFamily,
    }}>
      {/* Title */}
      <div style={{
        position: 'absolute', top: 30, left: 0, right: 0, textAlign: 'center',
      }}>
        <h1 style={{
          fontSize: 56, color: PAI_THEME.colors.text, margin: 0,
          opacity: titleOp, transform: `scale(${titleScale})`,
        }}>
          Bohr Transition — Electron Drop, Photon Emitted
        </h1>
        <p style={{
          fontSize: 26, color: PAI_THEME.colors.accentLight, marginTop: 6, fontStyle: 'italic',
          opacity: subOp,
        }}>
          n = 3 → n = 2 in hydrogen.   Photon energy = E₃ − E₂ ≈ 1.89 eV   →   λ = 656.3 nm  (H-α, red)
        </p>
      </div>

      <svg width={1920} height={1080} viewBox="0 0 1920 1080" style={{ position: 'absolute', inset: 0, opacity: atomOp }}>
        <defs>
          <radialGradient id="photon-glow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor={PAI_THEME.colors.photon} stopOpacity={1} />
            <stop offset="60%" stopColor={PAI_THEME.colors.photon} stopOpacity={0.5} />
            <stop offset="100%" stopColor={PAI_THEME.colors.photon} stopOpacity={0} />
          </radialGradient>
          <marker id="drop-arrow" viewBox="0 0 10 10" refX={5} refY={10} markerWidth={6} markerHeight={6} orient="auto">
            <path d="M 0 0 L 5 10 L 10 0 z" fill={PAI_THEME.colors.error} />
          </marker>
        </defs>

        {/* ── Bohr shells ─────────────────────────────────────────────── */}
        {SHELL_R.map((r, i) => (
          <g key={i}>
            <circle cx={ATOM_CX} cy={ATOM_CY} r={r}
              fill="none"
              stroke={i === 1 || i === 2 ? PAI_THEME.colors.textMuted : PAI_THEME.colors.textDark}
              strokeWidth={2}
              strokeDasharray="6 6" />
            <text x={ATOM_CX + r + 12} y={ATOM_CY - 4}
              fill={PAI_THEME.colors.textMuted} fontSize={22} fontWeight={700}>
              n = {i + 1}
            </text>
          </g>
        ))}

        {/* Nucleus */}
        <circle cx={ATOM_CX} cy={ATOM_CY} r={NUCLEUS_R}
          fill={PAI_THEME.colors.proton}
          stroke={PAI_THEME.colors.text} strokeWidth={3} />
        <text x={ATOM_CX} y={ATOM_CY + 9}
          fill={PAI_THEME.colors.text} fontSize={28} fontWeight={700} textAnchor="middle">
          +
        </text>

        {/* Electron */}
        <circle cx={electronX} cy={electronY} r={ELECTRON_R}
          fill={PAI_THEME.colors.electron}
          stroke={PAI_THEME.colors.text} strokeWidth={2.5} />
        <text x={electronX} y={electronY + 5}
          fill={PAI_THEME.colors.text} fontSize={16} fontWeight={700} textAnchor="middle">
          e⁻
        </text>

        {/* Photon */}
        {photonVisible && (
          <g>
            <circle cx={photonX} cy={photonY} r={28} fill="url(#photon-glow)" />
            <circle cx={photonX} cy={photonY} r={10}
              fill={PAI_THEME.colors.photon} stroke={PAI_THEME.colors.text} strokeWidth={2} />
            <text x={photonX} y={photonY + 5}
              fill={PAI_THEME.colors.text} fontSize={14} fontWeight={700} textAnchor="middle">ν</text>
          </g>
        )}

        {/* ── Energy ladder ───────────────────────────────────────────── */}
        <g>
          <text x={LADDER_X + LADDER_WIDTH / 2} y={LADDER_TOP - 30}
            fill={PAI_THEME.colors.text} fontSize={22} fontWeight={700} textAnchor="middle">
            Energy
          </text>
          {[1, 2, 3].map((n) => (
            <g key={n}>
              <line x1={LADDER_X} y1={ladderY(n)} x2={LADDER_X + LADDER_WIDTH} y2={ladderY(n)}
                stroke={PAI_THEME.colors.textMuted} strokeWidth={3} />
              <text x={LADDER_X + LADDER_WIDTH + 10} y={ladderY(n) + 8}
                fill={PAI_THEME.colors.textMuted} fontSize={20} fontWeight={700}>
                n = {n}
              </text>
            </g>
          ))}
          {/* Transition arrow from n=3 to n=2 (highlighted during drop) */}
          <line
            x1={LADDER_X + LADDER_WIDTH / 2} y1={ladderY(3)}
            x2={LADDER_X + LADDER_WIDTH / 2} y2={ladderY(2)}
            stroke={PAI_THEME.colors.error}
            strokeWidth={4}
            opacity={transitionArrowOp}
            markerEnd="url(#drop-arrow)" />
          <text
            x={LADDER_X + LADDER_WIDTH / 2 + 14}
            y={(ladderY(3) + ladderY(2)) / 2}
            fill={PAI_THEME.colors.error} fontSize={18} fontWeight={700}
            opacity={transitionArrowOp}>
            ΔE
          </text>
        </g>

        {/* ── Spectrum strip ──────────────────────────────────────────── */}
        <g>
          <rect x={SPEC_X} y={SPEC_Y} width={SPEC_W} height={SPEC_H}
            fill="#0f172a" stroke={PAI_THEME.colors.text} strokeWidth={2} />
          {/* Wavelength axis */}
          {[400, 450, 500, 550, 600, 650, 700].map((nm) => {
            const px = SPEC_X + ((nm - NM_MIN) / (NM_MAX - NM_MIN)) * SPEC_W;
            return (
              <g key={nm}>
                <line x1={px} y1={SPEC_Y + SPEC_H} x2={px} y2={SPEC_Y + SPEC_H + 8}
                  stroke={PAI_THEME.colors.textMuted} strokeWidth={1} />
                <text x={px} y={SPEC_Y + SPEC_H + 28}
                  fill={PAI_THEME.colors.textMuted} fontSize={16} textAnchor="middle">{nm}</text>
              </g>
            );
          })}
          <text x={SPEC_X + SPEC_W / 2} y={SPEC_Y + SPEC_H + 56}
            fill={PAI_THEME.colors.text} fontSize={20} fontWeight={700} textAnchor="middle">
            wavelength λ (nm)
          </text>

          {/* H-α line — pulses brighter when photon arrives */}
          <line
            x1={halphaPx} y1={SPEC_Y - lineGlow / 2}
            x2={halphaPx} y2={SPEC_Y + SPEC_H + lineGlow / 2}
            stroke="#ef4444"
            strokeWidth={5}
            opacity={lineBrightness}
            style={{ filter: lineGlow > 4 ? `drop-shadow(0 0 ${lineGlow}px #ef4444)` : undefined }} />
          <text x={halphaPx} y={SPEC_Y - 18}
            fill="#ef4444" fontSize={20} fontWeight={700} textAnchor="middle"
            opacity={lineBrightness}>
            H-α   656.3 nm
          </text>
        </g>
      </svg>

      {/* Caption */}
      <div style={{
        position: 'absolute', top: 990, left: 0, right: 0, textAlign: 'center',
        fontSize: 28, fontWeight: 700,
        color: PAI_THEME.colors.text,
        opacity: captionOp,
      }}>
        One photon per drop. Each spectral line is one fixed energy gap. The pattern is hydrogen's fingerprint.
      </div>
    </AbsoluteFill>
  );
};
