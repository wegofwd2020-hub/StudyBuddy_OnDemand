import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate, spring, useVideoConfig } from 'remotion';
import { PAI_THEME } from '../theme';

/**
 * Animated conic sections.
 *
 * 5 phases × 150 frames = 750 frames + 30-frame outro caption = 780 frames (26 s @ 30 fps).
 *
 *   Phase 0  introduce the double cone (no slicing plane yet)
 *   Phase 1  slice perpendicular to the axis              → CIRCLE
 *   Phase 2  tilt the plane                               → ELLIPSE
 *   Phase 3  tilt parallel to a generator (slant edge)    → PARABOLA
 *   Phase 4  tilt steeper, intersecting both nappes       → HYPERBOLA
 *
 * Layout (1920×1080):
 *   Left:   side-view of the double cone with the slicing plane (animated tilt + drift)
 *   Right:  the curve produced by that slice, plotted in xy with focus/directrix/asymptote markers
 *           appropriate to the conic
 *   Top:    title + phase pills
 *   Bottom: takeaway caption (fades in over the last second)
 */

const PHASE_FRAMES = 150;

// ---------- Phase definitions ------------------------------------------------

type Phase = {
  name: string;
  conic: 'none' | 'circle' | 'ellipse' | 'parabola' | 'hyperbola';
  // Tilt of the slicing plane in degrees (0 = horizontal, 90 = vertical).
  // Plane is drawn relative to the axis of the cone (vertical axis, z up).
  planeTiltDeg: number;
  // Vertical drift of the plane through the cone (in cone-axis units).
  planeOffset: number;
  description: string;
  equation: string;
};

const PHASES: Phase[] = [
  {
    name: 'The double cone',
    conic: 'none',
    planeTiltDeg: 0,
    planeOffset: 0,   // hidden
    description: 'A cone has TWO nappes that meet at the apex. Slice it with a plane — the cross-section is a conic.',
    equation: '',
  },
  {
    name: 'Circle',
    conic: 'circle',
    planeTiltDeg: 0,
    planeOffset: 1.5,
    description: 'Plane perpendicular to the axis  ⇒  every point of the slice is the same distance from the axis.',
    equation: 'x²  +  y²  =  r²',
  },
  {
    name: 'Ellipse',
    conic: 'ellipse',
    planeTiltDeg: 25,
    planeOffset: 1.2,
    description: 'Tilt the plane (still cutting only one nappe)  ⇒  closed oval bounded curve.',
    equation: 'x²/a²  +  y²/b²  =  1',
  },
  {
    name: 'Parabola',
    conic: 'parabola',
    planeTiltDeg: 45,
    planeOffset: 1.0,
    description: 'Tilt parallel to a generator (slant edge)  ⇒  an open, single-branch curve. Eccentricity e = 1.',
    equation: 'y²  =  4 p x',
  },
  {
    name: 'Hyperbola',
    conic: 'hyperbola',
    planeTiltDeg: 75,
    planeOffset: 0.6,
    description: 'Tilt steeper than the slant  ⇒  the plane meets BOTH nappes, producing two branches.',
    equation: 'x²/a²  −  y²/b²  =  1',
  },
];

// ---------- Helpers ----------------------------------------------------------

const easeOutCubic = (t: number) => 1 - Math.pow(1 - t, 3);

// Linear interpolate two phases for smooth transition.
const lerp = (a: number, b: number, t: number) => a + (b - a) * t;

// ---------- Cone + plane drawing (left panel) -------------------------------

type ConePanelProps = {
  cx: number;        // panel centre x
  cy: number;        // panel centre y (cone apex sits here)
  scale: number;     // pixels per cone-axis-unit
  planeTiltDeg: number;
  planeOffset: number;       // vertical position of plane centre (in axis units; positive = upper nappe)
  showPlane: boolean;
};

const ConePanel: React.FC<ConePanelProps> = ({
  cx, cy, scale, planeTiltDeg, planeOffset, showPlane,
}) => {
  // Cone half-angle: 30 degrees (so generators have slope 1/tan(30) ≈ 1.732 in z per unit r)
  // For drawing simplicity, the cone is parameterised by radius r at height ±h, with r = h*tan(30°).
  const tan30 = Math.tan((30 * Math.PI) / 180);

  // Top nappe: at height z, cross-section is a circle of radius z * tan30 (z>0).
  // We draw the cone in 2D using a side projection with a small horizontal "perspective" widening
  // to fake 3D, plus elliptical end-caps for the visible top and bottom.

  const H = 3.2;                 // half-height of each nappe in axis units
  const Rtop = H * tan30;        // radius at the top of the upper nappe

  const sx = (xUnits: number) => cx + xUnits * scale;
  const sy = (yUnits: number) => cy - yUnits * scale;

  // Cone outline (left + right generators of upper + lower nappes)
  const upperLeft  = `M ${sx(0)} ${sy(0)} L ${sx(-Rtop)} ${sy(H)}`;
  const upperRight = `M ${sx(0)} ${sy(0)} L ${sx( Rtop)} ${sy(H)}`;
  const lowerLeft  = `M ${sx(0)} ${sy(0)} L ${sx(-Rtop)} ${sy(-H)}`;
  const lowerRight = `M ${sx(0)} ${sy(0)} L ${sx( Rtop)} ${sy(-H)}`;

  // Top + bottom rim ellipses (the cone's visible "hoops" at z = ±H)
  const rimRx = Rtop * scale;
  const rimRy = Rtop * scale * 0.32;     // foreshortened — fakes 3D perspective

  // Slicing plane: tilted by planeTiltDeg around the y-axis (out of the page).
  // The plane is rendered as an ellipse in 2D (its trace + foreshortened depth).
  // Plane "horizontal extent" inside the cone depends on cone radius at the cut height.
  const tiltRad = (planeTiltDeg * Math.PI) / 180;
  const planeHalfW = Rtop * 1.55;             // a bit wider than the cone, sticks out
  const planeHalfH = planeHalfW * 0.32;        // foreshortening for the visible thickness
  const planeY = planeOffset;
  // When the plane tilts, we apply a 2D rotation to its outline ellipse around its centre.
  const planeRot = -planeTiltDeg;  // negative because screen-y flipped

  return (
    <g>
      {/* Back rim of upper nappe (hidden behind cone in real perspective) — draw faintly as dashed half */}
      <ellipse
        cx={sx(0)} cy={sy(H)} rx={rimRx} ry={rimRy}
        fill="none" stroke={PAI_THEME.colors.textDark} strokeWidth={2}
        strokeDasharray="4 6"
        opacity={0.5}
      />
      {/* Back rim of lower nappe */}
      <ellipse
        cx={sx(0)} cy={sy(-H)} rx={rimRx} ry={rimRy}
        fill="none" stroke={PAI_THEME.colors.textDark} strokeWidth={2}
        strokeDasharray="4 6"
        opacity={0.5}
      />

      {/* Cone faces (filled) — give the surface a faint wash to read as 3D */}
      <path
        d={`M ${sx(-Rtop)} ${sy(H)} L ${sx(0)} ${sy(0)} L ${sx(-Rtop)} ${sy(-H)} Z`}
        fill={PAI_THEME.colors.coolWash} stroke="none"
      />
      <path
        d={`M ${sx( Rtop)} ${sy(H)} L ${sx(0)} ${sy(0)} L ${sx( Rtop)} ${sy(-H)} Z`}
        fill={PAI_THEME.colors.coolWash} stroke="none"
      />

      {/* Generator lines */}
      <path d={upperLeft}  stroke={PAI_THEME.colors.accentLight} strokeWidth={2.2} fill="none" />
      <path d={upperRight} stroke={PAI_THEME.colors.accentLight} strokeWidth={2.2} fill="none" />
      <path d={lowerLeft}  stroke={PAI_THEME.colors.accentLight} strokeWidth={2.2} fill="none" />
      <path d={lowerRight} stroke={PAI_THEME.colors.accentLight} strokeWidth={2.2} fill="none" />

      {/* Front rims of both nappes (solid arcs over the lower half of each ellipse) */}
      <path
        d={`M ${sx(-Rtop)} ${sy(H)} A ${rimRx} ${rimRy} 0 0 0 ${sx(Rtop)} ${sy(H)}`}
        fill="none" stroke={PAI_THEME.colors.accent} strokeWidth={3}
      />
      <path
        d={`M ${sx(-Rtop)} ${sy(-H)} A ${rimRx} ${rimRy} 0 0 0 ${sx(Rtop)} ${sy(-H)}`}
        fill="none" stroke={PAI_THEME.colors.accent} strokeWidth={3}
      />

      {/* Apex marker */}
      <circle cx={sx(0)} cy={sy(0)} r={5} fill={PAI_THEME.colors.warning} stroke="white" strokeWidth={1.5} />
      <text x={sx(0) + 12} y={sy(0) + 6} fill={PAI_THEME.colors.warning}
        fontSize={20} fontWeight={700}>apex</text>

      {/* Axis */}
      <line
        x1={sx(0)} y1={sy(-H - 0.4)} x2={sx(0)} y2={sy(H + 0.4)}
        stroke={PAI_THEME.colors.textMuted} strokeWidth={1.2}
        strokeDasharray="4 4"
      />

      {/* Slicing plane */}
      {showPlane && (
        <g transform={`translate(${sx(0)} ${sy(planeY)}) rotate(${planeRot})`}>
          {/* Filled (semi-transparent) plane — drawn as ellipse to fake depth */}
          <ellipse
            cx={0} cy={0}
            rx={planeHalfW * scale}
            ry={planeHalfH * scale}
            fill="rgba(245, 158, 11, 0.20)"
            stroke={PAI_THEME.colors.warning}
            strokeWidth={2.5}
          />
          {/* Edge highlight — a chord across the front, indicates plane orientation */}
          <line
            x1={-planeHalfW * scale} y1={0}
            x2={ planeHalfW * scale} y2={0}
            stroke={PAI_THEME.colors.warning}
            strokeWidth={3}
          />
        </g>
      )}
    </g>
  );
};

// ---------- Conic plot (right panel) ----------------------------------------

type ConicPlotProps = {
  cx: number;
  cy: number;
  morph: number;        // 0 → previous conic outline, 1 → current conic outline
  prevConic: Phase['conic'];
  currConic: Phase['conic'];
};

const ConicPlot: React.FC<ConicPlotProps> = ({ cx, cy, morph, prevConic, currConic }) => {
  // Plot range x ∈ [-7, 7], y ∈ [-5, 5];  scale 50 px/unit → frame 700×500 wide
  const SX = 50;
  const SY = 50;
  const sxP = (x: number) => cx + x * SX;
  const syP = (y: number) => cy - y * SY;

  // Sample each conic as a list of points (x, y) — choose canonical examples that read clearly:
  //   circle:    x² + y² = 16          (r = 4)
  //   ellipse:   x²/25 + y²/9 = 1      (a=5, b=3)
  //   parabola:  y² = 4x               (focus 1,0 ; directrix x = -1)
  //   hyperbola: x²/9 − y²/16 = 1      (a=3, b=4, c=5)
  type Pt = { x: number; y: number };
  const pointsFor = (c: Phase['conic']): Pt[] => {
    if (c === 'circle') {
      const out: Pt[] = [];
      const N = 200;
      const r = 4;
      for (let i = 0; i <= N; i++) {
        const t = (i / N) * 2 * Math.PI;
        out.push({ x: r * Math.cos(t), y: r * Math.sin(t) });
      }
      return out;
    }
    if (c === 'ellipse') {
      const out: Pt[] = [];
      const N = 200;
      for (let i = 0; i <= N; i++) {
        const t = (i / N) * 2 * Math.PI;
        out.push({ x: 5 * Math.cos(t), y: 3 * Math.sin(t) });
      }
      return out;
    }
    if (c === 'parabola') {
      // sample y from -4.4 to 4.4 to keep within the plot frame
      const out: Pt[] = [];
      const N = 200;
      for (let i = 0; i <= N; i++) {
        const y = -4.4 + (i / N) * 8.8;
        out.push({ x: (y * y) / 4, y });
      }
      return out;
    }
    if (c === 'hyperbola') {
      // Two branches.  For animation we return them concatenated with a separator (NaN handled by caller).
      const out: Pt[] = [];
      const N = 100;
      // Right branch (x ≥ 3)
      for (let i = 0; i <= N; i++) {
        const t = -1.4 + (i / N) * 2.8;     // sinh parameter
        const cosh = (Math.exp(t) + Math.exp(-t)) / 2;
        const sinh = (Math.exp(t) - Math.exp(-t)) / 2;
        out.push({ x: 3 * cosh, y: 4 * sinh });
      }
      out.push({ x: NaN, y: NaN });   // gap between branches
      // Left branch (x ≤ -3)
      for (let i = 0; i <= N; i++) {
        const t = -1.4 + (i / N) * 2.8;
        const cosh = (Math.exp(t) + Math.exp(-t)) / 2;
        const sinh = (Math.exp(t) - Math.exp(-t)) / 2;
        out.push({ x: -3 * cosh, y: 4 * sinh });
      }
      return out;
    }
    return [];
  };

  const buildPath = (pts: Pt[]) => {
    if (pts.length === 0) return '';
    const segs: string[] = [];
    let mode: 'M' | 'L' = 'M';
    for (const p of pts) {
      if (!Number.isFinite(p.x) || !Number.isFinite(p.y)) {
        mode = 'M';
        continue;
      }
      segs.push(`${mode} ${sxP(p.x).toFixed(1)} ${syP(p.y).toFixed(1)}`);
      mode = 'L';
    }
    return segs.join(' ');
  };

  // Crossfade morph: render prev with (1 - morph), curr with morph
  const prevPath = buildPath(pointsFor(prevConic));
  const currPath = buildPath(pointsFor(currConic));

  // Frame for the right panel
  const frameX = cx - 350;
  const frameY = cy - 250;
  const frameW = 700;
  const frameH = 500;

  // Grid (every 1 unit)
  const vGrid: number[] = [];
  for (let x = -7; x <= 7; x++) if (x !== 0) vGrid.push(x);
  const hGrid: number[] = [];
  for (let y = -5; y <= 5; y++) if (y !== 0) hGrid.push(y);

  // Tick labels
  const xTicks = [-6, -3, 3, 6];
  const yTicks = [-4, -2, 2, 4];

  // Foci / vertices for the current conic (decorations)
  const decorations = () => {
    const elems: React.ReactNode[] = [];
    const lblColor = PAI_THEME.colors.warning;
    const ptColor = PAI_THEME.colors.warning;
    if (currConic === 'circle') {
      elems.push(<circle key="cc" cx={sxP(0)} cy={syP(0)} r={6} fill={ptColor} stroke="white" strokeWidth={2.5} />);
      elems.push(<text key="ccl" x={sxP(0) + 12} y={syP(0) - 12} fill={lblColor} fontSize={20} fontWeight={700}>center (0, 0)</text>);
      elems.push(<line key="cr" x1={sxP(0)} y1={syP(0)} x2={sxP(4)} y2={syP(0)} stroke={lblColor} strokeWidth={3} strokeLinecap="round" />);
      elems.push(<text key="crl" x={sxP(2)} y={syP(0) - 14} fill={lblColor} fontSize={18}>r = 4</text>);
    } else if (currConic === 'ellipse') {
      // foci (-4, 0) and (4, 0)
      elems.push(<circle key="f1" cx={sxP(-4)} cy={syP(0)} r={6} fill={ptColor} stroke="white" strokeWidth={2.5} />);
      elems.push(<circle key="f2" cx={sxP( 4)} cy={syP(0)} r={6} fill={ptColor} stroke="white" strokeWidth={2.5} />);
      elems.push(<text key="f1l" x={sxP(-4)} y={syP(0) + 30} fill={lblColor} fontSize={18} textAnchor="middle">F₁(−4, 0)</text>);
      elems.push(<text key="f2l" x={sxP( 4)} y={syP(0) + 30} fill={lblColor} fontSize={18} textAnchor="middle">F₂(4, 0)</text>);
    } else if (currConic === 'parabola') {
      // focus (1, 0); directrix x = -1
      elems.push(<line key="dir" x1={sxP(-1)} y1={syP(-4.5)} x2={sxP(-1)} y2={syP(4.5)} stroke="#f87171" strokeWidth={2.5} strokeDasharray="6 5" />);
      elems.push(<text key="dirl" x={sxP(-1) - 8} y={syP(-3.8)} fill="#f87171" fontSize={18} textAnchor="end">directrix  x = −1</text>);
      elems.push(<circle key="f" cx={sxP(1)} cy={syP(0)} r={6} fill={ptColor} stroke="white" strokeWidth={2.5} />);
      elems.push(<text key="fl" x={sxP(1) + 12} y={syP(0) + 22} fill={lblColor} fontSize={18}>F(1, 0)</text>);
    } else if (currConic === 'hyperbola') {
      // foci (-5, 0), (5, 0); asymptotes y = ±(4/3)x
      const aslope = 4 / 3;
      elems.push(<line key="a1" x1={sxP(-7)} y1={syP(-aslope * 7)} x2={sxP(7)} y2={syP(aslope * 7)} stroke={PAI_THEME.colors.accentLight} strokeWidth={1.6} strokeDasharray="6 5" />);
      elems.push(<line key="a2" x1={sxP(-7)} y1={syP( aslope * 7)} x2={sxP(7)} y2={syP(-aslope * 7)} stroke={PAI_THEME.colors.accentLight} strokeWidth={1.6} strokeDasharray="6 5" />);
      elems.push(<circle key="f1" cx={sxP(-5)} cy={syP(0)} r={6} fill={ptColor} stroke="white" strokeWidth={2.5} />);
      elems.push(<circle key="f2" cx={sxP( 5)} cy={syP(0)} r={6} fill={ptColor} stroke="white" strokeWidth={2.5} />);
      elems.push(<text key="f1l" x={sxP(-5)} y={syP(0) + 30} fill={lblColor} fontSize={18} textAnchor="middle">F₁(−5, 0)</text>);
      elems.push(<text key="f2l" x={sxP( 5)} y={syP(0) + 30} fill={lblColor} fontSize={18} textAnchor="middle">F₂(5, 0)</text>);
    }
    return elems;
  };

  return (
    <g>
      {/* Frame */}
      <rect x={frameX} y={frameY} width={frameW} height={frameH}
        fill={PAI_THEME.colors.backgroundAlt} stroke={PAI_THEME.colors.textDark}
        strokeWidth={2} rx={12} />

      {/* Grid */}
      {vGrid.map((g) => (
        <line key={`vg-${g}`} x1={sxP(g)} y1={frameY + 10} x2={sxP(g)} y2={frameY + frameH - 10}
          stroke={PAI_THEME.colors.background} strokeWidth={1} />
      ))}
      {hGrid.map((g) => (
        <line key={`hg-${g}`} x1={frameX + 10} y1={syP(g)} x2={frameX + frameW - 10} y2={syP(g)}
          stroke={PAI_THEME.colors.background} strokeWidth={1} />
      ))}

      {/* Axes */}
      <line x1={frameX + 10} y1={syP(0)} x2={frameX + frameW - 10} y2={syP(0)}
        stroke={PAI_THEME.colors.textMuted} strokeWidth={1.8} />
      <line x1={sxP(0)} y1={frameY + 10} x2={sxP(0)} y2={frameY + frameH - 10}
        stroke={PAI_THEME.colors.textMuted} strokeWidth={1.8} />

      {/* Tick labels */}
      {xTicks.map((x) => (
        <text key={`xt-${x}`} x={sxP(x)} y={syP(0) + 22} fontSize={18}
          fill={PAI_THEME.colors.textMuted} textAnchor="middle">{x}</text>
      ))}
      {yTicks.map((y) => (
        <text key={`yt-${y}`} x={sxP(0) - 12} y={syP(y) + 6} fontSize={18}
          fill={PAI_THEME.colors.textMuted} textAnchor="end">{y}</text>
      ))}

      {/* Previous conic, fading out */}
      {prevConic !== 'none' && morph < 1 && (
        <path d={prevPath}
          fill="none" stroke={PAI_THEME.colors.accent}
          strokeWidth={5} strokeLinecap="round"
          opacity={1 - morph} />
      )}
      {/* Current conic, fading in */}
      {currConic !== 'none' && (
        <path d={currPath}
          fill="none" stroke={PAI_THEME.colors.accent}
          strokeWidth={5} strokeLinecap="round"
          opacity={morph} />
      )}

      {/* Decorations only render when fully on the current conic */}
      <g opacity={Math.max(0, morph - 0.5) * 2}>{decorations()}</g>
    </g>
  );
};

// ---------- Main scene -------------------------------------------------------

export const ConicSectionsScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const totalPhases = PHASES.length;
  const phaseIdx = Math.min(totalPhases - 1, Math.floor(frame / PHASE_FRAMES));
  const localFrame = frame - phaseIdx * PHASE_FRAMES;

  // Tween over the first 60% of each phase
  const t = phaseIdx === 0
    ? interpolate(localFrame, [0, PHASE_FRAMES * 0.6], [0, 1], {
        extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
      })
    : interpolate(localFrame, [0, PHASE_FRAMES * 0.6], [0, 1], {
        extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
      });
  const morph = easeOutCubic(t);

  const prev = PHASES[Math.max(0, phaseIdx - 1)];
  const curr = PHASES[phaseIdx];

  // Plane parameters interpolated between phases
  const planeTilt = lerp(prev.planeTiltDeg, curr.planeTiltDeg, morph);
  const planeOff  = lerp(prev.planeOffset,  curr.planeOffset,  morph);
  const showPlane = !(phaseIdx === 0 && morph < 0.95);
  // For phase 0 specifically the plane should not be visible at all.
  const showPlaneActual = phaseIdx === 0 ? false : showPlane;

  // Title pop-in
  const titleScale = spring({ frame, fps, config: PAI_THEME.animation.springDefault });
  const titleOpacity = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: 'clamp' });

  // Outro caption (last 30 frames)
  const captionOp = interpolate(frame, [750, 780], [0, 1], { extrapolateRight: 'clamp' });

  return (
    <AbsoluteFill style={{
      backgroundColor: PAI_THEME.colors.background,
      padding: 40,
      flexDirection: 'column',
      justifyContent: 'flex-start',
      alignItems: 'center',
      fontFamily: PAI_THEME.typography.fontFamily,
    }}>
      <h1 style={{
        fontSize: 56,
        color: PAI_THEME.colors.text,
        margin: '12px 0 4px',
        opacity: titleOpacity,
        transform: `scale(${titleScale})`,
        textAlign: 'center',
      }}>
        Conic Sections
      </h1>
      <p style={{
        fontSize: 26,
        color: PAI_THEME.colors.accentLight,
        margin: '0 0 18px',
        fontStyle: 'italic',
      }}>
        Slice a double cone — the cross-section is a circle, ellipse, parabola, or hyperbola
      </p>

      {/* Phase pills */}
      <div style={{ display: 'flex', gap: 14, marginBottom: 6, flexWrap: 'wrap', justifyContent: 'center' }}>
        {PHASES.map((p, i) => {
          const active = i === phaseIdx;
          const past = i < phaseIdx;
          return (
            <div key={i} style={{
              padding: '8px 14px',
              borderRadius: 8,
              background: active ? PAI_THEME.colors.accent : 'transparent',
              color: active ? 'white' : (past ? PAI_THEME.colors.accentLight : PAI_THEME.colors.textMuted),
              fontSize: 18,
              fontWeight: active ? 600 : 400,
              border: `1px solid ${active ? PAI_THEME.colors.accent : PAI_THEME.colors.textDark}`,
            }}>
              {i}: {p.name}
            </div>
          );
        })}
      </div>

      {/* Description + equation row */}
      <div style={{
        display: 'flex',
        gap: 32,
        marginBottom: 8,
        height: 56,
        alignItems: 'center',
        justifyContent: 'center',
        maxWidth: 1700,
        textAlign: 'center',
      }}>
        <div style={{ color: PAI_THEME.colors.textMuted, fontSize: 22, flex: '1 1 auto', maxWidth: 1100 }}>
          {curr.description}
        </div>
        {curr.equation && (
          <div style={{
            color: PAI_THEME.colors.accentLight,
            fontSize: 28,
            fontStyle: 'italic',
            padding: '4px 18px',
            border: `1.5px solid ${PAI_THEME.colors.accent}`,
            borderRadius: 8,
            whiteSpace: 'nowrap',
          }}>
            {curr.equation}
          </div>
        )}
      </div>

      {/* Two-panel SVG */}
      <div style={{ background: PAI_THEME.colors.backgroundAlt, borderRadius: 16, padding: 12, marginTop: 4 }}>
        <svg width={1760} height={760}>
          {/* Left panel: cone with slicing plane */}
          <ConePanel
            cx={400}
            cy={380}
            scale={90}
            planeTiltDeg={planeTilt}
            planeOffset={planeOff}
            showPlane={showPlaneActual}
          />

          {/* Vertical separator */}
          <line x1={860} y1={40} x2={860} y2={720}
            stroke={PAI_THEME.colors.textDark} strokeWidth={1.5}
            strokeDasharray="6 6" />

          {/* Section labels */}
          <text x={400} y={68} fill={PAI_THEME.colors.textMuted} fontSize={22} textAnchor="middle">
            The double cone + slicing plane
          </text>
          <text x={1290} y={68} fill={PAI_THEME.colors.textMuted} fontSize={22} textAnchor="middle">
            Cross-section curve in the slicing plane
          </text>

          {/* Right panel: conic plot */}
          <ConicPlot
            cx={1290}
            cy={400}
            morph={morph}
            prevConic={prev.conic}
            currConic={curr.conic}
          />
        </svg>
      </div>

      {/* Outro caption */}
      <div style={{
        marginTop: 14,
        color: PAI_THEME.colors.text,
        fontSize: 26,
        opacity: captionOp,
        textAlign: 'center',
        maxWidth: 1700,
      }}>
        One family, four curves —
        &nbsp;<span style={{ color: PAI_THEME.colors.accentLight }}>circle</span>,
        &nbsp;<span style={{ color: PAI_THEME.colors.accentLight }}>ellipse</span>,
        &nbsp;<span style={{ color: PAI_THEME.colors.accentLight }}>parabola</span>,
        &nbsp;<span style={{ color: PAI_THEME.colors.accentLight }}>hyperbola</span>
        &nbsp;— distinguished by the angle of the cut.
      </div>
    </AbsoluteFill>
  );
};
