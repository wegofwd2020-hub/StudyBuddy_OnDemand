export const ADOPTION_STATUS_ACCENT = {
  active: "#4f46e5", // indigo-600 — matches BookMarked icon
  deactivated: "#78716c", // stone-500 — neutral muted
  archived: "#d97706", // amber-600 — platform-archived
} as const;

export type AdoptionAccentKey = keyof typeof ADOPTION_STATUS_ACCENT;
