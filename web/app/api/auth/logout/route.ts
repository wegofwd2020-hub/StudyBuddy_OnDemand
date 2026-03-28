import { NextResponse } from "next/server";

export async function GET() {
  const response = NextResponse.redirect(
    new URL("/", process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000"),
  );
  // Clear the dev session cookie
  response.cookies.set("sb_dev_session", "", { maxAge: 0, path: "/" });
  return response;
}
