import type { NextRequest } from "next/server";
import type { NextResponse } from "next/server";
import { getAuth0 } from "./lib/auth0";

export async function proxy(request: NextRequest): Promise<NextResponse> {
  try {
    return await getAuth0().middleware(request);
  } catch (error) {
    // Auth0 domain resolution may fail in dev/local environment. Allow request to proceed.
    return undefined as unknown as NextResponse;
  }
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|sitemap.xml|robots.txt).*)"],
};
