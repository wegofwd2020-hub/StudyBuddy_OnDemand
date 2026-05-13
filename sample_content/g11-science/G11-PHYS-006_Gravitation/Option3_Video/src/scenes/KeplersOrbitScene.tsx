import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate, spring, useVideoConfig } from 'remotion';
import { PAI_THEME } from '../theme';

/**
 * Kepler's Second Law — equal areas in equal times.
 *
 * A planet orbits the sun on an elliptical path with the sun at one focus.
 * As the orbit progresses we shade four sectors of equal duration ΔT — they
 * have visibly different angular widths but the same area, illustrating that
 * the line from sun to planet sweeps out equal areas in equal times.
 *
 * Phases (frames at 30fps, total 28 s = 840 frames):
 *   0–60     title fade-in
 *   60–180   orbit + sun fade-in, planet placed at periapsis
 *   180–660  planet completes one full orbit; four sectors drawn at
 *            t = 0..ΔT, ΔT..2ΔT, 2ΔT..3ΔT, 3ΔT..4ΔT (where ΔT = T/4 for visual rhythm,
 *            but each sector is drawn during its real time slice — slowest near
 *            apoapsis (long thin), fastest near periapsis (short fat)).
 *   660–840  closing caption "equal areas, equal times"
 */

// ─── Geometry constants ───────────────────────────────────────────────────────
const W = 1920;
const H = 1080;

// Centre of the ellipse on screen.
const CX = W / 2;
const CY = H / 2 + 30;

// Ellipse semi-axes (pixels). Eccentricity e ≈ 0.6 chosen for visual drama.
const A = 480;  // semi-major
const E = 0.6;
const B = A * Math.sqrt(1 - E * E);   // semi-minor

// Sun is at one focus of the ellipse, offset by a*e from centre toward periapsis.
const SUN_X = CX + A * E;
const SUN_Y = CY;

// Solve Kepler's equation M = E_anom − e sin E_anom for E_anom by Newton iteration.
function solveKepler(M: number, e: number): number {
  let Eanom = M;
  for (let i = 0; i < 8; i++) {
    Eanom = Eanom - (Eanom - e * Math.sin(Eanom) - M) / (1 - e * Math.cos(Eanom));
  }
  return Eanom;
}

// Position on the ellipse (relative to centre) as a function of mean anomaly M.
// Periapsis (closest point) at +X side near sun.
function positionAt(M: number): { x: number; y: number } {
  const Eanom = solveKepler(M, E);
  const x = A * (Math.cos(Eanom) - E);   // shift so origin is at focus? no — keep at centre
  const y = B * Math.sin(Eanom);
  // We want periapsis on the +X side near the sun. Currently when Eanom = 0,
  // x = A * (1 - e) which is the periapsis distance from centre. Sun is at +A*e
  // from centre, so periapsis radial distance = A - A*e = A(1-e). ✓
  return { x, y };
}

// Build an SVG-path string for the closed elliptical orbit (debug guide).
function ellipsePath(): string {
  const N = 200;
  const pts: string[] = [];
  for (let i = 0; i <= N; i++) {
    const M = (i / N) * 2 * Math.PI;
    const p = positionAt(M);
    pts.push(`${(CX + p.x).toFixed(1)},${(CY + p.y).toFixed(1)}`);
  }
  return pts.join(' ');
}

// Build a filled sector polygon — sun, then arc samples between two mean anomalies.
function sectorPolygon(M1: number, M2: number, samples = 40): string {
  const pts: string[] = [`${SUN_X.toFixed(1)},${SUN_Y.toFixed(1)}`];
  for (let i = 0; i <= samples; i++) {
    const M = M1 + (i / samples) * (M2 - M1);
    const p = positionAt(M);
    pts.push(`${(CX + p.x).toFixed(1)},${(CY + p.y).toFixed(1)}`);
  }
  return pts.join(' ');
}

// ─── Component ─────────────────────────────────────────────────────────────────
export const KeplersOrbitScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Title fade
  const titleScale = spring({ frame, fps, config: PAI_THEME.animation.springDefault });
  const titleOp = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: 'clamp' });
  const subOp = interpolate(frame, [30, 60], [0, 1], { extrapolateRight: 'clamp' });

  // Orbit + sun fade in
  const sysOp = interpolate(frame, [60, 180], [0, 1], { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' });

  // Planet animation: complete one orbit between frames 180 and 660 (480 frames).
  // Mean anomaly M progresses linearly with time → 2π over the orbit window.
  const orbitProgress = interpolate(frame, [180, 660], [0, 1], { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' });
  const M_now = orbitProgress * 2 * Math.PI;

  // Four sector boundaries at M = 0, π/2, π, 3π/2, 2π — each represents an equal time slice.
  const sectorEdges = [0, Math.PI / 2, Math.PI, (3 * Math.PI) / 2, 2 * Math.PI];

  // Sector colours (use accent + variants).
  const sectorColors = [
    'rgba(167, 139, 250, 0.42)',  // periapsis sector — fastest, fattest
    'rgba(139, 92, 246, 0.34)',
    'rgba(99, 102, 241, 0.30)',
    'rgba(167, 139, 250, 0.28)',  // apoapsis sector — slowest, thinnest
  ];

  // Determine which sectors are "complete" or "in progress".
  const sectors = sectorEdges.slice(0, -1).map((M1, i) => {
    const M2 = sectorEdges[i + 1];
    const startedFrac = Math.max(0, Math.min(1, (M_now - M1) / (M2 - M1)));
    return { M1, M2, fillTo: M1 + startedFrac * (M2 - M1), drawn: M_now >= M1 };
  });

  // Planet position right now
  const ppos = positionAt(M_now);
  const planetX = CX + ppos.x;
  const planetY = CY + ppos.y;

  // Caption
  const captionOp = interpolate(frame, [660, 720], [0, 1], { extrapolateRight: 'clamp' });

  // Pre-compute sector labels (centroid approx — pick midpoint of arc).
  const sectorLabels = sectorEdges.slice(0, -1).map((M1, i) => {
    const M2 = sectorEdges[i + 1];
    const Mmid = (M1 + M2) / 2;
    const p = positionAt(Mmid);
    // Centroid is roughly halfway between sun and the arc midpoint.
    const lx = (SUN_X + (CX + p.x)) / 2;
    const ly = (SUN_Y + (CY + p.y)) / 2;
    return { i, lx, ly };
  });

  return (
    <AbsoluteFill style={{
      background: `linear-gradient(135deg, ${PAI_THEME.colors.background}, ${PAI_THEME.colors.backgroundAlt})`,
      flexDirection: 'column', alignItems: 'center', padding: 40,
      fontFamily: PAI_THEME.typography.fontFamily,
    }}>
      <h1 style={{
        fontSize: 56, color: PAI_THEME.colors.text, margin: '20px 0 4px',
        opacity: titleOp, transform: `scale(${titleScale})`, textAlign: 'center',
      }}>
        Kepler's Second Law
      </h1>
      <p style={{
        fontSize: 26, color: PAI_THEME.colors.accentLight, margin: '0 0 16px',
        opacity: subOp, fontStyle: 'italic', textAlign: 'center',
      }}>
        A line from the Sun to a planet sweeps out equal areas in equal times.
      </p>

      <svg width={W} height={H - 200} style={{ position: 'absolute', top: 140, left: 0 }}>
        {/* Background star field — sparse */}
        <g opacity={sysOp * 0.6}>
          {Array.from({ length: 60 }).map((_, k) => {
            const sx = ((k * 137) % W);
            const sy = ((k * 91) % (H - 200));
            const r = 0.8 + ((k * 7) % 13) / 10;
            return <circle key={`star-${k}`} cx={sx} cy={sy} r={r} fill={PAI_THEME.colors.textMuted} />;
          })}
        </g>

        {/* Orbit guide ellipse (faint dashed) */}
        <polyline points={ellipsePath()}
          fill="none"
          stroke={PAI_THEME.colors.textMuted}
          strokeWidth={2}
          strokeDasharray="8 6"
          opacity={sysOp * 0.5} />

        {/* Centre cross of ellipse (subtle reference) */}
        <g opacity={sysOp * 0.25}>
          <line x1={CX - 14} y1={CY} x2={CX + 14} y2={CY} stroke={PAI_THEME.colors.textDark} strokeWidth={1} />
          <line x1={CX} y1={CY - 14} x2={CX} y2={CY + 14} stroke={PAI_THEME.colors.textDark} strokeWidth={1} />
        </g>

        {/* Filled sectors — drawn progressively as planet sweeps through them */}
        {sectors.map((s, i) =>
          s.drawn ? (
            <polygon key={`sector-${i}`}
              points={sectorPolygon(s.M1, s.fillTo)}
              fill={sectorColors[i]}
              stroke={PAI_THEME.colors.accentLight}
              strokeWidth={1.5}
              opacity={sysOp} />
          ) : null
        )}

        {/* Sector labels with "Δt" — fade in as each sector completes */}
        {sectorLabels.map((lab) => {
          const s = sectors[lab.i];
          const completedFrac = (M_now - s.M1) / (s.M2 - s.M1);
          const labelOp = sysOp * Math.max(0, Math.min(1, completedFrac));
          return (
            <g key={`lab-${lab.i}`} opacity={labelOp}>
              <text x={lab.lx} y={lab.ly} fill={PAI_THEME.colors.text}
                fontSize={28} fontWeight={700} textAnchor="middle">
                Δt
              </text>
              <text x={lab.lx} y={lab.ly + 28} fill={PAI_THEME.colors.accentLight}
                fontSize={20} fontStyle="italic" textAnchor="middle">
                area = A
              </text>
            </g>
          );
        })}

        {/* Sun at focus */}
        <g opacity={sysOp}>
          <defs>
            <radialGradient id="ke-sun" cx="0.5" cy="0.5" r="0.5">
              <stop offset="0%" stopColor="#fde68a" />
              <stop offset="60%" stopColor="#f59e0b" />
              <stop offset="100%" stopColor="#b45309" />
            </radialGradient>
          </defs>
          <circle cx={SUN_X} cy={SUN_Y} r={32} fill="url(#ke-sun)" stroke="#7c2d12" strokeWidth={2} />
          <text x={SUN_X} y={SUN_Y + 64} fill={PAI_THEME.colors.warning}
            fontSize={26} fontWeight={700} textAnchor="middle">Sun</text>
          <text x={SUN_X} y={SUN_Y + 90} fill={PAI_THEME.colors.textMuted}
            fontSize={18} fontStyle="italic" textAnchor="middle">(at one focus)</text>
        </g>

        {/* Line from sun to planet (the "radius vector") */}
        <line x1={SUN_X} y1={SUN_Y} x2={planetX} y2={planetY}
          stroke={PAI_THEME.colors.accent} strokeWidth={3}
          opacity={sysOp} />

        {/* Planet */}
        <g opacity={sysOp}>
          <circle cx={planetX} cy={planetY} r={18}
            fill={PAI_THEME.colors.info} stroke="white" strokeWidth={3} />
          <circle cx={planetX} cy={planetY} r={28}
            fill="none" stroke={PAI_THEME.colors.accentLight} strokeWidth={1}
            opacity={0.5} />
        </g>

        {/* Periapsis & apoapsis markers (faint) */}
        <g opacity={sysOp * 0.5}>
          <circle cx={CX + A * (1 - E)} cy={CY} r={5} fill={PAI_THEME.colors.warning} />
          <text x={CX + A * (1 - E) + 14} y={CY + 6} fill={PAI_THEME.colors.warning}
            fontSize={18} fontStyle="italic">periapsis (fastest)</text>
          <circle cx={CX - A * (1 + E)} cy={CY} r={5} fill={PAI_THEME.colors.textMuted} />
          <text x={CX - A * (1 + E) - 14} y={CY + 6} fill={PAI_THEME.colors.textMuted}
            fontSize={18} fontStyle="italic" textAnchor="end">apoapsis (slowest)</text>
        </g>
      </svg>

      <div style={{
        position: 'absolute', bottom: 60, left: 0, right: 0,
        color: PAI_THEME.colors.text, fontSize: 30,
        opacity: captionOp, textAlign: 'center', maxWidth: 1600, margin: '0 auto',
      }}>
        Same Δt → same swept area.    Near the Sun the planet moves <em>fast</em>; far away it crawls.
      </div>

      {/* HUD: live mean anomaly */}
      <div style={{
        position: 'absolute', top: 160, right: 60,
        color: PAI_THEME.colors.textMuted,
        fontFamily: PAI_THEME.typography.fontFamilyMono, fontSize: 22,
        opacity: sysOp,
      }}>
        orbit progress: {(orbitProgress * 100).toFixed(0)}%
      </div>
    </AbsoluteFill>
  );
};
