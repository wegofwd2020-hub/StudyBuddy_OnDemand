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

export async function saveAccountSettings(
  settings: Partial<AccountSettings>,
): Promise<void> {
  await api.patch("/auth/settings", settings);
}
