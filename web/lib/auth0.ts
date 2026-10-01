import { Auth0Client } from "@auth0/nextjs-auth0/server";

let auth0: any = null;

class StubAuth0Client {
  async getSession() {
    return null;
  }
}

export function getAuth0() {
  if (!auth0) {
    const domain = process.env.AUTH0_DOMAIN;
    // Skip Auth0 if domain is invalid (localhost, empty, etc.)
    if (!domain || domain.includes("localhost")) {
      auth0 = new StubAuth0Client();
    } else {
      try {
        auth0 = new Auth0Client({
          domain,
          clientId: process.env.AUTH0_CLIENT_ID,
          clientSecret: process.env.AUTH0_CLIENT_SECRET,
          secret: process.env.AUTH0_SECRET,
        });
      } catch {
        auth0 = new StubAuth0Client();
      }
    }
  }
  return auth0;
}
