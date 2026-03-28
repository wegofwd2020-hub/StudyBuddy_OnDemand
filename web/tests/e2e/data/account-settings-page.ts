/**
 * Test data for section 2.12 — Account Settings (`/account/settings`)
 * Covers TC-IDs: STU-36, STU-37, STU-38, STU-39, STU-40
 *
 * Auth note: /account/settings requires a real Auth0 session for E2E.
 * Unit tests mock getAccountSettings() and saveAccountSettings() directly.
 *
 * Backend API routes for E2E page.route() interception:
 *   GET   /api/v1/auth/settings → MOCK_ACCOUNT_SETTINGS
 *   PATCH /api/v1/auth/settings → 200 OK
 */

import type { AccountSettings } from "@/lib/api/settings";

// ---------------------------------------------------------------------------
// Mock settings — all fields populated (STU-36..STU-39)
// ---------------------------------------------------------------------------

export const MOCK_ACCOUNT_SETTINGS: AccountSettings = {
  display_name: "Alex Johnson",
  locale: "en",
  notifications: {
    streak_reminders: true,
    weekly_summary: false,
    quiz_nudges: true,
  },
};

// ---------------------------------------------------------------------------
// Updated settings variants (STU-37, STU-38, STU-39)
// ---------------------------------------------------------------------------

export const UPDATED_DISPLAY_NAME = "Alex Smith";

export const SETTINGS_WITH_FRENCH: AccountSettings = {
  ...MOCK_ACCOUNT_SETTINGS,
  locale: "fr",
};

export const SETTINGS_NOTIFICATIONS_ALL_OFF: AccountSettings = {
  ...MOCK_ACCOUNT_SETTINGS,
  notifications: {
    streak_reminders: false,
    weekly_summary: false,
    quiz_nudges: false,
  },
};

// ---------------------------------------------------------------------------
// Expected UI strings
// (title key matches useTranslations("settings_screen") — mock returns key)
// ---------------------------------------------------------------------------

export const SETTINGS_STRINGS = {
  title:              "title",
  saveBtn:            "save_btn",
  savingText:         "Saving…",
  savedText:          "Saved",
  profileHeading:     "Profile",
  languageHeading:    "Language",
  notifHeading:       "Notifications",
  displayNameLabel:   "Display name",
  displayNamePlaceholder: "Your name",
  loadError:          "Failed to load settings.",
  saveError:          "Failed to save settings. Please try again.",
  // Locale button labels
  english:            "English",
  french:             "Français",
  spanish:            "Español",
  // Notification labels
  streakReminders:    "Streak reminders",
  weeklySummary:      "Weekly summary",
  quizNudges:         "Quiz nudges",
} as const;
