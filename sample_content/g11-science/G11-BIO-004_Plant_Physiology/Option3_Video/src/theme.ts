/**
 * PAI Theme for Remotion — Plant Physiology variant (G11-BIO-004).
 * Mirrors the BIO-001 / BIO-002 palette with plantae-greens leading.
 */

export const PAI_THEME = {
  colors: {
    background: '#0f172a',
    backgroundAlt: '#1e293b',
    backgroundDark: '#020617',

    accent: '#15803d',         // plantae green (the unit's lead colour)
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

    // Photosynthesis-specific palette
    sunlight: '#fbbf24',        // gold for photons
    sunlightHot: '#f59e0b',
    chloroplastBody: '#15803d',
    chloroplastDark: '#14532d',
    thylakoid: '#22c55e',
    stroma: '#bbf7d0',
    water: '#3b82f6',
    waterDeep: '#1e3a8a',
    oxygen: '#dbeafe',
    co2: '#94a3b8',
    glucose: '#fce7f3',
    glucoseStroke: '#be185d',
    atp: '#fef3c7',
    atpStroke: '#d97706',
    nadph: '#fce7f3',
    nadphStroke: '#be185d',

    // Kingdom palette — preserved for visual continuity with BIO-001 / BIO-002
    plantae: '#15803d',
    monera: '#7c3aed',
    animalia: '#2b6cb0',
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
