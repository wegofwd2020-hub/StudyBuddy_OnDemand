// Port of derivePalette() from SBS_2/handoff/reference/LibraryShared.jsx.
// Converts a single accent hex into a 5-stop palette via HSL tinting so a
// school admin can re-skin a subject by picking one color.

export interface SubjectPalette {
  accent: string;
  bg1: string; // ~96% lightness — soft card/section backgrounds
  bg2: string; // ~80% lightness — hover states
  ink: string; // ~22% lightness — text on light backgrounds
  border: string; // ~88% lightness — subtle rule/ring
}

export function getSubjectPalette(accentHex: string): SubjectPalette {
  const h = accentHex.replace("#", "");
  const r = parseInt(h.slice(0, 2), 16) / 255;
  const g = parseInt(h.slice(2, 4), 16) / 255;
  const b = parseInt(h.slice(4, 6), 16) / 255;

  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const lit = (max + min) / 2;

  let hue = 0;
  let sat = 0;

  if (max !== min) {
    const d = max - min;
    sat = lit > 0.5 ? d / (2 - max - min) : d / (max + min);
    switch (max) {
      case r:
        hue = ((g - b) / d + (g < b ? 6 : 0)) * 60;
        break;
      case g:
        hue = ((b - r) / d + 2) * 60;
        break;
      case b:
        hue = ((r - g) / d + 4) * 60;
        break;
    }
  }

  const s = Math.round(sat * 100);
  const sc = Math.min(100, s + 5);

  return {
    accent: accentHex,
    bg1: `hsl(${Math.round(hue)} ${sc}% 96%)`,
    bg2: `hsl(${Math.round(hue)} ${sc}% 80%)`,
    ink: `hsl(${Math.round(hue)} ${Math.min(100, s + 10)}% 22%)`,
    border: `hsl(${Math.round(hue)} ${s}% 88%)`,
  };
}
