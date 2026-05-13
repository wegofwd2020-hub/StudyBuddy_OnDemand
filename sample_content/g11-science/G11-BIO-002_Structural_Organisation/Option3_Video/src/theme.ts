/**
 * PAI Theme for Remotion — biology variant (G11-BIO-002).
 * Mirrors the BIO-001 palette: kingdom-keyed and rank-keyed colours, plus
 * level-of-organisation accents (cell → tissue → organ → system → organism)
 * borrowed from the rank ladder for visual continuity across the BIO catalogue.
 */

export const PAI_THEME = {
  colors: {
    background: '#0f172a',
    backgroundAlt: '#1e293b',
    backgroundDark: '#020617',

    accent: '#15803d',        // biology-leaning green accent
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

    // Level-of-organisation palette (cell → organism)
    // Reuses the BIO-001 rank colours for visual continuity.
    cell: '#be185d',          // pink — narrowest
    tissue: '#dc2626',        // red
    organ: '#d97706',         // amber
    system: '#15803d',        // green
    organism: '#2b6cb0',      // blue — broadest
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
