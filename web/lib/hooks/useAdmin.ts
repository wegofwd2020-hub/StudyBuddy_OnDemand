/**
 * Decode the admin JWT stored in localStorage and expose key claims.
 * Admin console components use this hook to get admin_id and role.
 */
"use client";

import { useState, useEffect } from "react";

export type AdminRole = "developer" | "tester" | "product_admin" | "super_admin";

export interface AdminClaims {
  admin_id: string;
  role: AdminRole;
}

const ROLE_RANK: Record<AdminRole, number> = {
  developer: 0,
  tester: 1,
  product_admin: 2,
  super_admin: 3,
};

export function hasPermission(role: AdminRole, minRole: AdminRole): boolean {
  return ROLE_RANK[role] >= ROLE_RANK[minRole];
}

function decodeJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const base64 = token.split(".")[1];
    const json = atob(base64.replace(/-/g, "+").replace(/_/g, "/"));
    return JSON.parse(json);
  } catch {
    return null;
  }
}

const VALID_ROLES = new Set<AdminRole>([
  "developer",
  "tester",
  "product_admin",
  "super_admin",
]);

export function useAdmin(): AdminClaims | null {
  const [admin, setAdmin] = useState<AdminClaims | null>(null);

  useEffect(() => {
    const token = localStorage.getItem("sb_admin_token");
    if (!token) return;
    const payload = decodeJwtPayload(token);
    if (!payload) return;
    const admin_id = payload.admin_id as string | undefined;
    const role = payload.role as AdminRole | undefined;
    if (!admin_id || !role || !VALID_ROLES.has(role)) return;
    setAdmin({ admin_id, role });
  }, []);

  return admin;
}
