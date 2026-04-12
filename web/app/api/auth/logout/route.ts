import { NextRequest, NextResponse } from "next/server";

export async function GET(request: NextRequest) {
  const isLocalAuth = request.cookies.has("sb_local_teacher_session");

  // Local-auth users go back to the school login page; everyone else to home.
  const destination = isLocalAuth
    ? "/school/login"
    : "/";

  const response = NextResponse.redirect(
    new URL(destination, process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000"),
  );

  // Clear all session cookies regardless of auth track.
  response.cookies.set("sb_dev_session", "", { maxAge: 0, path: "/" });
  response.cookies.set("sb_local_teacher_session", "", { maxAge: 0, path: "/" });
  response.cookies.set("sb_teacher_session", "", { maxAge: 0, path: "/" });

  return response;
}
