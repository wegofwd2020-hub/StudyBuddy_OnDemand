/**
 * web/lib/dev-session.ts
 *
 * Server-side helper for the dev bypass session.
 * The /dev-login page sets a "sb_dev_session" cookie (base64-encoded JSON)
 * so that server layouts can read name/email without Auth0 being configured.
 *
 * Only used in development; safe to import in any server component.
 */

import { cookies } from "next/headers";

export interface DevSession {
  user: { name: string; email: string };
}

export async function getDevSession(): Promise<DevSession | null> {
  try {
    const store = await cookies();
    const raw = store.get("sb_dev_session")?.value;
    if (!raw) return null;
    const data = JSON.parse(Buffer.from(raw, "base64url").toString("utf-8"));
    if (!data?.email) return null;
    return { user: { name: data.name ?? data.email, email: data.email } };
  } catch {
    return null;
  }
}
