/**
 * TaxonomicHierarchyScene — Animated taxonomic zoom from Domain to Species.
 *
 * Eight ranks revealed one at a time, each accompanied by:
 *   - The rank label (Domain → Kingdom → Phylum → ...)
 *   - The classification of Homo sapiens at that rank (Eukarya → Animalia → ...)
 *   - A widening "rank stack" on the left that visually shows the ladder filling.
 *   - The "universe of organisms" set on the right, contracting at each step.
 *
 * The zoom metaphor: at Domain we are looking at all of life. At Species we
 * have narrowed to one organism — Homo sapiens. The contracting circle on the
 * right ("organisms remaining") visualises the narrowing.
 *
 * Frames @ 30fps (26 s total = 780 frames):
 *   0–60       Title fades in
 *   60–150     Rank 1: Domain → Eukarya
 *   150–230    Rank 2: Kingdom → Animalia
 *   230–310    Rank 3: Phylum → Chordata
 *   310–390    Rank 4: Class → Mammalia
 *   390–470    Rank 5: Order → Primates
 *   470–550    Rank 6: Family → Hominidae
 *   550–630    Rank 7: Genus → Homo
 *   630–720    Rank 8: Species → Homo sapiens (highlight pulse)
 *   720–780    Closing caption fades in
 */
import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate, spring, useVideoConfig } from 'remotion';
import { PAI_THEME } from '../theme';

// ── Hierarchy data ────────────────────────────────────────────────────────────
type Rank = {
  rank: string;
  taxon: string;
  italic: boolean;
  hint: string;
  // Approximate "organisms in this group" — used for the shrinking circle.
  // Numbers are illustrative; we only need them on a relative log scale.
  populationLog: number;
  color: string;
};

const RANKS: Rank[] = [
  { rank: 'Domain',  taxon: 'Eukarya',     italic: false, hint: 'true nucleus, organelles',          populationLog: 8.5, color: PAI_THEME.colors.domain },
  { rank: 'Kingdom', taxon: 'Animalia',    italic: false, hint: 'multicellular, ingestion',          populationLog: 7.2, color: PAI_THEME.colors.kingdom },
  { rank: 'Phylum',  taxon: 'Chordata',    italic: false, hint: 'notochord, dorsal nerve cord',      populationLog: 5.0, color: PAI_THEME.colors.phylum },
  { rank: 'Class',   taxon: 'Mammalia',    italic: false, hint: 'hair, mammary glands',              populationLog: 3.8, color: PAI_THEME.colors.class },
  { rank: 'Order',   taxon: 'Primates',    italic: false, hint: 'grasping hands, large brain',       populationLog: 2.6, color: PAI_THEME.colors.order },
  { rank: 'Family',  taxon: 'Hominidae',   italic: false, hint: 'great apes',                        populationLog: 1.0, color: PAI_THEME.colors.family },
  { rank: 'Genus',   taxon: 'Homo',        italic: true,  hint: 'humans + extinct relatives',        populationLog: 0.3, color: PAI_THEME.colors.genus },
  { rank: 'Species', taxon: 'Homo sapiens',italic: true,  hint: 'wise human — modern us',            populationLog: 0.0, color: PAI_THEME.colors.species },
];

// Frame anchors — 30 fps. Each rank gets ~80 frames.
const F_TITLE_END = 60;
const F_RANK_DURATION = 80;
const F_CAPTION_START = F_TITLE_END + RANKS.length * F_RANK_DURATION; // = 700
const F_CAPTION_END = F_CAPTION_START + 60;

const W = 1920;
const H = 1080;

// Layout
const LADDER_X = 140;
const LADDER_TOP = 150;
const LADDER_ROW_H = 96;
const LADDER_W = 720;

const CIRCLE_CX = 1380;
const CIRCLE_CY = 540;
const CIRCLE_R_MAX = 320;
const CIRCLE_R_MIN = 18;

export const TaxonomicHierarchyScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // ── Title ────────────────────────────────────────────────────────────────
  const titleSpring = spring({ frame, fps, config: PAI_THEME.animation.springDefault });
  const titleOp = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: 'clamp' });
  const subOp = interpolate(frame, [20, 60], [0, 1], { extrapolateRight: 'clamp' });

  // ── Determine current rank index (0-based) ───────────────────────────────
  const elapsedAfterTitle = Math.max(0, frame - F_TITLE_END);
  const currentRankIdx = Math.min(
    RANKS.length - 1,
    Math.floor(elapsedAfterTitle / F_RANK_DURATION),
  );

  // For the shrinking universe-circle, animate radius based on currentRankIdx + smooth interpolation.
  const rankProgress = Math.min(
    RANKS.length - 1,
    elapsedAfterTitle / F_RANK_DURATION,
  );
  // Map populationLog to radius: log 8.5 → CIRCLE_R_MAX, log 0 → CIRCLE_R_MIN
  // Interpolate between the discrete RANKS[i] population values smoothly.
  const lo = Math.floor(rankProgress);
  const hi = Math.min(RANKS.length - 1, lo + 1);
  const t = rankProgress - lo;
  const popLog = RANKS[lo].populationLog * (1 - t) + RANKS[hi].populationLog * t;
  const circleR = interpolate(popLog, [0, 8.5], [CIRCLE_R_MIN, CIRCLE_R_MAX]);

  // ── Closing caption ──────────────────────────────────────────────────────
  const captionOp = interpolate(
    frame,
    [F_CAPTION_START, F_CAPTION_END],
    [0, 1],
    { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' },
  );

  return (
    <AbsoluteFill style={{
      background: `linear-gradient(135deg, ${PAI_THEME.colors.background}, ${PAI_THEME.colors.backgroundAlt})`,
      fontFamily: PAI_THEME.typography.fontFamily,
    }}>
      {/* ── Title ────────────────────────────────────────────────────── */}
      <div style={{
        position: 'absolute', top: 30, left: 0, right: 0, textAlign: 'center',
      }}>
        <h1 style={{
          fontSize: 56, color: PAI_THEME.colors.text, margin: 0,
          opacity: titleOp, transform: `scale(${titleSpring})`,
        }}>
          From All of Life to One Species
        </h1>
        <p style={{
          fontSize: 26, color: PAI_THEME.colors.accentLight, marginTop: 6, fontStyle: 'italic',
          opacity: subOp,
        }}>
          Eight steps narrow the universe of organisms down to <em>Homo sapiens</em>.
        </p>
      </div>

      {/* ── Ladder of ranks (left) ──────────────────────────────────── */}
      <svg
        width={W} height={H} viewBox={`0 0 ${W} ${H}`}
        style={{ position: 'absolute', inset: 0 }}
      >
        {/* Backbone */}
        <line
          x1={LADDER_X - 30}
          y1={LADDER_TOP - 20}
          x2={LADDER_X - 30}
          y2={LADDER_TOP + RANKS.length * LADDER_ROW_H + 10}
          stroke={PAI_THEME.colors.textDark}
          strokeWidth={3}
        />
        <text
          x={LADDER_X - 60}
          y={LADDER_TOP + (RANKS.length * LADDER_ROW_H) / 2}
          fill={PAI_THEME.colors.textMuted}
          fontSize={20}
          fontWeight={700}
          textAnchor="middle"
          transform={`rotate(-90 ${LADDER_X - 60} ${LADDER_TOP + (RANKS.length * LADDER_ROW_H) / 2})`}
        >
          broad → specific
        </text>

        {/* Rank rows */}
        {RANKS.map((r, i) => {
          const yTop = LADDER_TOP + i * LADDER_ROW_H;
          const revealStart = F_TITLE_END + i * F_RANK_DURATION;
          const revealEnd = revealStart + 30;

          const rowOp = interpolate(
            frame, [revealStart, revealEnd], [0, 1],
            { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
          );
          const rowSlide = interpolate(
            frame, [revealStart, revealEnd], [-40, 0],
            { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
          );

          // Ladder rows narrow visually as they go down (mirrors the SVG ladder)
          const indent = i * 18;
          const widthForRow = LADDER_W - i * 36;

          // Pulse highlight when this rank becomes "current"
          const pulse = i === currentRankIdx
            ? interpolate(
                frame,
                [revealStart, revealStart + 15, revealEnd],
                [1.0, 1.06, 1.0],
                { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
              )
            : 1.0;

          // Final-species pulse (extra emphasis on the last row)
          const finalPulse = i === RANKS.length - 1
            ? interpolate(
                frame,
                [630, 660, 690, 720],
                [1.0, 1.08, 1.0, 1.08],
                { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
              )
            : 1.0;

          const scale = pulse * finalPulse;

          return (
            <g
              key={r.rank}
              transform={`translate(${LADDER_X + indent + rowSlide}, ${yTop})`}
              opacity={rowOp}
            >
              <g transform={`scale(${scale}) translate(${(1 - scale) * widthForRow / 2}, 0)`}>
                <rect
                  x={0} y={0}
                  width={widthForRow} height={LADDER_ROW_H - 18}
                  rx={10}
                  fill={r.color}
                  opacity={0.18}
                  stroke={r.color}
                  strokeWidth={2.5}
                />
                <text
                  x={20}
                  y={32}
                  fill={r.color}
                  fontSize={22}
                  fontWeight={700}
                >
                  {r.rank}
                </text>
                <text
                  x={20}
                  y={62}
                  fill={PAI_THEME.colors.text}
                  fontSize={36}
                  fontWeight={700}
                  fontStyle={r.italic ? 'italic' : 'normal'}
                >
                  {r.taxon}
                </text>
                <text
                  x={widthForRow - 18}
                  y={62}
                  fill={PAI_THEME.colors.textMuted}
                  fontSize={16}
                  textAnchor="end"
                  fontStyle="italic"
                >
                  {r.hint}
                </text>
              </g>
            </g>
          );
        })}

        {/* ── Universe-circle (right) ─────────────────────────────── */}
        <g>
          {/* Outer reference ring (always full size, faint) */}
          <circle
            cx={CIRCLE_CX}
            cy={CIRCLE_CY}
            r={CIRCLE_R_MAX}
            fill="none"
            stroke={PAI_THEME.colors.textDark}
            strokeWidth={1.5}
            strokeDasharray="6 6"
          />
          <text
            x={CIRCLE_CX}
            y={CIRCLE_CY - CIRCLE_R_MAX - 28}
            fill={PAI_THEME.colors.textMuted}
            fontSize={20}
            fontWeight={700}
            textAnchor="middle"
          >
            organisms remaining
          </text>

          {/* Filled shrinking circle */}
          <circle
            cx={CIRCLE_CX}
            cy={CIRCLE_CY}
            r={circleR}
            fill={RANKS[currentRankIdx].color}
            opacity={0.35}
            stroke={RANKS[currentRankIdx].color}
            strokeWidth={3}
          />

          {/* Centre label = current taxon */}
          <text
            x={CIRCLE_CX}
            y={CIRCLE_CY - 8}
            fill={PAI_THEME.colors.text}
            fontSize={32}
            fontWeight={700}
            textAnchor="middle"
            fontStyle={RANKS[currentRankIdx].italic ? 'italic' : 'normal'}
          >
            {RANKS[currentRankIdx].taxon}
          </text>
          <text
            x={CIRCLE_CX}
            y={CIRCLE_CY + 22}
            fill={PAI_THEME.colors.textMuted}
            fontSize={18}
            textAnchor="middle"
          >
            {RANKS[currentRankIdx].rank}
          </text>

          {/* Tick scale: log of organism count */}
          <text
            x={CIRCLE_CX}
            y={CIRCLE_CY + CIRCLE_R_MAX + 36}
            fill={PAI_THEME.colors.textMuted}
            fontSize={16}
            textAnchor="middle"
          >
            ~10^{popLog.toFixed(1)} organisms in this group
          </text>
        </g>
      </svg>

      {/* ── Closing caption ─────────────────────────────────────────── */}
      <div style={{
        position: 'absolute', top: 990, left: 0, right: 0, textAlign: 'center',
        fontSize: 28, fontWeight: 700,
        color: PAI_THEME.colors.text,
        opacity: captionOp,
      }}>
        Eight ranks. One species. The classification system is a search engine for life itself.
      </div>
    </AbsoluteFill>
  );
};
