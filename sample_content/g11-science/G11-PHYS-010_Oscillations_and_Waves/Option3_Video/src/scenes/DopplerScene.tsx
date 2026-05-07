/**
 * DopplerScene — a moving source emits circular wavefronts at a fixed period T.
 *
 * Physics:
 *   At each emission time t_e (with t_e = n·T_emit for integer n ≥ 0), the
 *   source is at position (x_s(t_e), y0). The wavefront emitted there has
 *   radius r(t) = c · (t − t_e) at scene time t.
 *
 *   Because the source moves rightward at v_s, successive wavefront centers
 *   shift rightward. With v_s < c, this crowds the wavefronts ahead of the
 *   source (apparent higher frequency to a stationary observer in front) and
 *   spreads them behind (lower frequency to a stationary observer behind).
 *
 *   Wavelength ahead:  λ_front = (c − v_s) · T_emit
 *   Wavelength behind: λ_back  = (c + v_s) · T_emit
 *
 * Frames @ 30fps (22s total = 660 frames):
 *   0–60   title + equations fade in
 *   60–660 animation (20 s)
 */
import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate, useVideoConfig, spring } from 'remotion';
import { PAI_THEME } from '../theme';

// ── Tunables (chosen for visual readability, not derived from real physics) ──
const C_PX = 150;          // wave speed in px/s
const VS_PX = 75;          // source speed in px/s (v_s/c = 0.5)
const T_EMIT = 0.6;        // seconds between wavefronts
const Y0 = 540;            // baseline y in canvas space (1080-tall canvas)
const X_START = 280;
const X_END = 1640;        // source travels this far over 20 s if v_s=68; we cap below
const ACTIVE_START_FRAME = 60;

export const DopplerScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const titleScale = spring({ frame, fps, config: PAI_THEME.animation.springDefault });
  const titleOp = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: 'clamp' });
  const subOp = interpolate(frame, [20, 60], [0, 1], { extrapolateRight: 'clamp' });

  const activeFrame = Math.max(0, frame - ACTIVE_START_FRAME);
  const t = activeFrame / fps;

  // Source position (clamped so it doesn't run off the canvas)
  const xs = Math.min(X_START + VS_PX * t, X_END);

  // Compute every wavefront emitted so far
  const wavefronts: Array<{ cx: number; cy: number; r: number; opacity: number }> = [];
  const lastEmissionN = Math.floor(t / T_EMIT);
  for (let n = 0; n <= lastEmissionN; n++) {
    const te = n * T_EMIT;
    const cx = Math.min(X_START + VS_PX * te, X_END);
    const cy = Y0;
    const r = C_PX * (t - te);
    if (r > 1200) continue; // off-canvas
    // Fade older wavefronts gently so the diagram stays readable
    const ageFrac = r / 1200;
    const opacity = Math.max(0.15, 1 - ageFrac * 0.7);
    wavefronts.push({ cx, cy, r, opacity });
  }

  return (
    <AbsoluteFill style={{
      background: `linear-gradient(135deg, ${PAI_THEME.colors.background}, ${PAI_THEME.colors.backgroundAlt})`,
      flexDirection: 'column', alignItems: 'center', padding: 30,
      fontFamily: PAI_THEME.typography.fontFamily,
    }}>
      <h1 style={{
        fontSize: 52, color: PAI_THEME.colors.text, margin: '8px 0 4px',
        opacity: titleOp, transform: `scale(${titleScale})`, textAlign: 'center',
      }}>
        Doppler Effect
      </h1>
      <p style={{
        fontSize: 26, color: PAI_THEME.colors.accentLight, margin: '0 0 4px',
        opacity: subOp, fontStyle: 'italic',
      }}>
        Source moving right at v<sub>s</sub> = 0.5 c    ·    λ<sub>front</sub> = (c − v<sub>s</sub>) T    ·    λ<sub>back</sub> = (c + v<sub>s</sub>) T
      </p>

      <svg width={1920} height={900} viewBox="0 0 1920 900">
        {/* Reference baseline */}
        <line x1={120} y1={Y0} x2={1800} y2={Y0}
          stroke={PAI_THEME.colors.textDark} strokeWidth={1} strokeDasharray="4 8" />

        {/* Wavefronts (back-to-front so newest is most visible) */}
        {wavefronts.map((w, i) => (
          <circle key={i}
            cx={w.cx} cy={w.cy} r={w.r}
            fill="none"
            stroke={PAI_THEME.colors.accentLight}
            strokeWidth={2.5}
            opacity={w.opacity} />
        ))}

        {/* Source */}
        <circle cx={xs} cy={Y0} r={20}
          fill={PAI_THEME.colors.warning}
          stroke={PAI_THEME.colors.text} strokeWidth={2.5} />
        {/* Source velocity arrow */}
        <line x1={xs} y1={Y0} x2={xs + 90} y2={Y0}
          stroke={PAI_THEME.colors.warning} strokeWidth={4}
          markerEnd="url(#vsArrow)" />
        <defs>
          <marker id="vsArrow" markerWidth={10} markerHeight={10} refX={9} refY={3} orient="auto">
            <polygon points="0 0, 10 3, 0 6" fill={PAI_THEME.colors.warning} />
          </marker>
          <marker id="obsArrow" markerWidth={10} markerHeight={10} refX={9} refY={3} orient="auto">
            <polygon points="0 0, 10 3, 0 6" fill={PAI_THEME.colors.text} />
          </marker>
        </defs>
        <text x={xs + 50} y={Y0 - 18}
          fill={PAI_THEME.colors.warning} fontSize={22} fontWeight={700} textAnchor="middle">
          v<tspan baselineShift="sub" fontSize={16}>s</tspan>
        </text>
        <text x={xs} y={Y0 + 56}
          fill={PAI_THEME.colors.text} fontSize={22} textAnchor="middle">
          source
        </text>

        {/* Forward (compressed) observer */}
        <g>
          <circle cx={1720} cy={Y0 - 220} r={14}
            fill={PAI_THEME.colors.success} stroke={PAI_THEME.colors.text} strokeWidth={2} />
          <text x={1720} y={Y0 - 248} fill={PAI_THEME.colors.success}
            fontSize={22} fontWeight={700} textAnchor="middle">
            Observer A
          </text>
          <text x={1720} y={Y0 - 220 + 140} fill={PAI_THEME.colors.success}
            fontSize={20} textAnchor="middle">
            ahead → higher frequency
          </text>
          <text x={1720} y={Y0 - 220 + 168} fill={PAI_THEME.colors.success}
            fontSize={20} textAnchor="middle">
            (waves crowd together)
          </text>
        </g>

        {/* Backward (rarefied) observer */}
        <g>
          <circle cx={200} cy={Y0 - 220} r={14}
            fill={PAI_THEME.colors.error} stroke={PAI_THEME.colors.text} strokeWidth={2} />
          <text x={200} y={Y0 - 248} fill={PAI_THEME.colors.error}
            fontSize={22} fontWeight={700} textAnchor="middle">
            Observer B
          </text>
          <text x={200} y={Y0 - 220 + 140} fill={PAI_THEME.colors.error}
            fontSize={20} textAnchor="middle">
            behind → lower frequency
          </text>
          <text x={200} y={Y0 - 220 + 168} fill={PAI_THEME.colors.error}
            fontSize={20} textAnchor="middle">
            (waves stretch apart)
          </text>
        </g>
      </svg>

      <div style={{
        color: PAI_THEME.colors.text, fontSize: 24,
        textAlign: 'center', maxWidth: 1700, marginTop: 4,
      }}>
        Wavefronts emitted every T seconds. The source moves between emissions, so each new wavefront's center is shifted in the direction of motion — compressing crests ahead and spreading them behind.
      </div>
    </AbsoluteFill>
  );
};
