/**
 * PAI Theme for Remotion — biology variant (G11-BIO-005).
 * Mirrors the BIO-001/002/003 palette: kingdom-keyed colours plus cardiovascular
 * phase accents (atrial systole / isovolumetric contraction / ejection /
 * isovolumetric relaxation / filling) for visual continuity across the BIO
 * catalogue.
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

    // Cardiac-cycle phase palette
    atrialSystole:           '#f59e0b',  // amber  — atria push
    isovolumetricContraction:'#b45309',  // dark amber
    ventricularEjection:     '#dc2626',  // red    — oxygen out
    isovolumetricRelaxation: '#7c3aed',  // purple — valves shut
    ventricularFilling:      '#2b6cb0',  // blue   — passive fill

    // Anatomical accents
    oxygenated:              '#dc2626',  // arterial red
    deoxygenated:            '#1e3a8a',  // venous blue
    chamberWall:             '#7f1d1d',
    valveOpen:               '#86efac',
    valveClosed:             '#94a3b8',
    aorta:                   '#dc2626',
    pulmonaryArtery:         '#3b82f6',
  },

  typography: {
    fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',

    title:    { fontSize: 72, fontWeight: 'bold' as const, lineHeight: 1.1 },
    subtitle: { fontSize: 48, fontWeight: '600' as const, lineHeight: 1.2 },
    heading:  { fontSize: 36, fontWeight: '600' as const, lineHeight: 1.3 },
    body:     { fontSize: 24, fontWeight: 'normal' as const, lineHeight: 1.5 },
    caption:  { fontSize: 18, fontWeight: 'normal' as const, lineHeight: 1.4 },
  },

  animation: {
    springFast:    { damping: 15, stiffness: 150 },
    springDefault: { damping: 12, stiffness: 100 },
    springSlow:    { damping: 10, stiffness: 80 },

    fadeFrames: 30,
    quickFade:  15,
    slowFade:   45,
  },
} as const;

export type PAITheme = typeof PAI_THEME;
