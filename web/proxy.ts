import type { NextRequest } from "next/server";
import type { NextResponse } from "next/server";
import { getAuth0 } from "./lib/auth0";

export async function proxy(request: NextRequest): Promise<NextResponse> {
  return await getAuth0().middleware(request);
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|sitemap.xml|robots.txt).*)"],
};
