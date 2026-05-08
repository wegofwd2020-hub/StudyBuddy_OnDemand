/**
 * pipeline/visual_templates/biology_cells.ts
 *
 * Class-specific palette for biology cell-anatomy catalogues.
 *
 * Lifted from `scripts/generate_biology_cells_visuals.ts` per #344
 * (Wave 6 phase C-8). Per the G6-SCI-001 MEMO, this 14-colour table is
 * the locked-in convention for every downstream biology unit
 * (G7-SCI-003, G9-SCI-005, G12-BIO-*).
 *
 * **Critical:** students bind colour to organelle identity. Do not
 * override these in per-unit generators — extend with new constants for
 * new organelles (mitochondrial cristae detail, peroxisomes, etc.) or
 * file a Wave-N PR that updates this table.
 *
 * Inline patterns (doubleMembrane, stackedFolds, Bézier blobs) live
 * inside figure functions in the generator and are deferred to Wave-7
 * (#345 to be filed). The palette alone is high-value — every downstream
 * biology unit must import from here for identity consistency.
 */

// ─────────────────────────────────────────────────────────────────────────
// Locked organelle palette — 14 colours
// ─────────────────────────────────────────────────────────────────────────

export const CYTOPLASM = "#fef9c3"; // very pale yellow-green
export const CELL_MEMBRANE = "#94a3b8"; // muted slate
export const CELL_WALL = "#a16207"; // amber-brown (plant only)
export const NUCLEUS = "#7c3aed"; // purple
export const NUCLEOLUS = "#a855f7"; // lighter purple
export const MITOCHONDRION = "#dc2626"; // red (energy)
export const CHLOROPLAST = "#16a34a"; // green
export const VACUOLE = "#7dd3fc"; // pale blue
export const GOLGI = "#f59e0b"; // amber
export const ER_ROUGH = "#ea580c"; // peach
export const ER_SMOOTH = "#fb923c"; // lighter peach
export const LYSOSOME = "#f472b6"; // pink
export const RIBOSOME = "#7c2d12"; // dark brown dots
export const CENTROSOME = "#64748b"; // slate

/**
 * Aggregate map for downstream code that wants to look up by organelle name.
 * Mirrors the individual exports above; safe to import either form.
 */
export const ORGANELLE_PALETTE = {
  cytoplasm: CYTOPLASM,
  cellMembrane: CELL_MEMBRANE,
  cellWall: CELL_WALL,
  nucleus: NUCLEUS,
  nucleolus: NUCLEOLUS,
  mitochondrion: MITOCHONDRION,
  chloroplast: CHLOROPLAST,
  vacuole: VACUOLE,
  golgi: GOLGI,
  erRough: ER_ROUGH,
  erSmooth: ER_SMOOTH,
  lysosome: LYSOSOME,
  ribosome: RIBOSOME,
  centrosome: CENTROSOME,
} as const;
