import api from "./client";

export interface NotificationPreferences {
  streak_reminders: boolean;
  weekly_summary: boolean;
  quiz_nudges: boolean;
}

export interface AccountSettings {
  display_name: string;
  locale: string;
  notifications: NotificationPreferences;
}

export async function getAccountSettings(): Promise<AccountSettings> {
  const res = await api.get<AccountSettings>("/auth/settings");
  return res.data;
}

/**
 * Save account settings. When the locale changed the backend re-mints the
 * student JWT (locale is authoritative from the token) and returns it here so
 * the caller can swap the stale token — otherwise the new language wouldn't
 * apply to content until the next login (#470).
 */
export async function saveAccountSettings(
  settings: Partial<AccountSettings>,
): Promise<{ token?: string }> {
  const res = await api.patch<{ token?: string }>("/auth/settings", settings);
  return res.data ?? {};
}
