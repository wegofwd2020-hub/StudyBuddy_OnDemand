/**
 * pipeline/visual_templates/chemistry_atom.ts
 *
 * Class-specific palette + (eventually) primitives for atomic-structure
 * catalogues.
 *
 * Lifted from `scripts/generate_chemistry_atom_visuals.ts` per #344
 * (Wave 6 phase C-9). The chemistry_atom generator was the largest
 * "all inline" generator in the corpus — its primitives (concentric
 * shells, orbital shapes, energy ladder, orbital boxes) live inside
 * figure functions and require per-figure refactoring to extract.
 *
 * **This module ships the locked particle palette today.** Inline-pattern
 * extraction (concentricShells, orbital, energyLadder, orbitalBoxRow,
 * miniBohrAtom) is deferred to Wave-7 (#345 to be filed) where each
 * extraction will get a byte-equivalence verification per figure.
 *
 * **Critical:** the particle palette must remain byte-identical across
 * every chemistry visual — students bind colour to particle identity.
 */

// ─────────────────────────────────────────────────────────────────────────
// Locked particle palette
//
// Carries identically into G7-SCI-001 (mini Bohr atoms in a periodic-table
// grid), G12-CHEM-* (transition metals, electrochemistry), and any future
// quantum-mechanics or atomic-structure unit. Inconsistency is the single
// biggest source of "this looks wrong" feedback in pilots.
// ─────────────────────────────────────────────────────────────────────────

export const PROTON = "#dc2626"; // red — matches periodic_table.ts PROTON
export const NEUTRON = "#64748b"; // slate
export const ELECTRON = "#2b6cb0"; // blue — matches periodic_table.ts ELECTRON
export const PHOTON = "#facc15"; // yellow

/**
 * Aggregate particle palette for downstream code that wants name-based lookup.
 */
export const PARTICLE_PALETTE = {
  proton: PROTON,
  neutron: NEUTRON,
  electron: ELECTRON,
  photon: PHOTON,
} as const;
