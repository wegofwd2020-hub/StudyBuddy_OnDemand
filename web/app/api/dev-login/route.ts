/**
 * web/app/api/dev-login/route.ts
 *
 * Server-side proxy for the backend POST /auth/dev-login endpoint.
 * The browser calls /api/dev-login (same origin) so there is no CORS issue.
 * Next.js server then forwards the request to the backend internally.
 */

import { NextRequest, NextResponse } from "next/server";

// INTERNAL_API_URL uses the Docker service name — works inside the container.
// Falls back to localhost for running Next.js outside Docker.
const BACKEND_URL = process.env.INTERNAL_API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export async function POST(req: NextRequest) {
  const body = await req.json();

  let res: Response;
  try {
    res = await fetch(`${BACKEND_URL}/auth/dev-login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch (err: unknown) {
    return NextResponse.json(
      { detail: `Backend unreachable: ${(err as Error).message}` },
      { status: 502 },
    );
  }

  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
