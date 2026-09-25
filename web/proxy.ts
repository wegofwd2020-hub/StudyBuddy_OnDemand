import type { NextRequest } from "next/server";
import type { NextResponse } from "next/server";
import { getAuth0 } from "./lib/auth0";

export async function proxy(request: NextRequest): Promise<NextResponse> {
  try {
    return await getAuth0().middleware(request);
  } catch (error) {
    // Auth0 domain resolution may fail in dev/local environment.
    if (process.env.NODE_ENV !== "production") {
      console.error("[auth0-middleware] Dev/test mode - allowing request through:", error);
      return undefined as unknown as NextResponse;
    }
    // Production: auth failures must not silently pass through
    console.error("[auth0-middleware] Production auth error:", error);
    throw error;
  }
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|sitemap.xml|robots.txt).*)"],
};
