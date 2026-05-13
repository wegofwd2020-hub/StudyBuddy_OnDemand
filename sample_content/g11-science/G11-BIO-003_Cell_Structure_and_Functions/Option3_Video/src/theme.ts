/**
 * PAI Theme for Remotion — biology variant (G11-BIO-003).
 * Mirrors the BIO-001/002 palette: kingdom-keyed colours plus cell-cycle phase
 * accents (G1 / S / G2 / M) for visual continuity across the BIO catalogue.
 */

export const PAI_THEME = {
  colors: {
    background: '#0f172a',
    backgroundAlt: '#1e293b',
    backgroundDark: '#020617',

    accent: '#15803d',
    accentLight: '#86efac',
    accentDark: '#14532d',
    accentMuted: '#22c55e',

    text: '#f1f5f9',
    textMuted: '#94a3b8',
    textDark: '#64748b',

    paperGround: '#F5F5F0',
    coolWash: 'rgba(21, 128, 61, 0.10)',
    warmWash: 'rgba(251, 191, 36, 0.10)',

    success: '#10b981',
    warning: '#f59e0b',
    error: '#ef4444',
    info: '#3b82f6',

    // Kingdom palette — matches BIO-001
    monera: '#7c3aed',
    protista: '#319795',
    fungi: '#b45309',
    plantae: '#15803d',
    animalia: '#2b6cb0',

    // Cell-cycle phase palette
    g1: '#2b6cb0',   // blue — gap 1 (growth)
    s:  '#15803d',   // green — DNA synthesis
    g2: '#b45309',   // amber — gap 2
    m:  '#dc2626',   // red — mitosis
    g0: '#94a3b8',   // grey — quiescent

    // Macromolecule accents
    chromatid: '#dc2626',
    spindle: '#7c3aed',
    nuclearEnvelope: '#1e3a8a',
    centrosome: '#f59e0b',
    checkpoint: '#f59e0b',
  },

  typography: {
    fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',

    title: { fontSize: 72, fontWeight: 'bold' as const, lineHeight: 1.1 },
    subtitle: { fontSize: 48, fontWeight: '600' as const, lineHeight: 1.2 },
    heading: { fontSize: 36, fontWeight: '600' as const, lineHeight: 1.3 },
    body: { fontSize: 24, fontWeight: 'normal' as const, lineHeight: 1.5 },
    caption: { fontSize: 18, fontWeight: 'normal' as const, lineHeight: 1.4 },
  },

  animation: {
    springFast: { damping: 15, stiffness: 150 },
    springDefault: { damping: 12, stiffness: 100 },
    springSlow: { damping: 10, stiffness: 80 },

    fadeFrames: 30,
    quickFade: 15,
    slowFade: 45,
  },
} as const;

export type PAITheme = typeof PAI_THEME;
