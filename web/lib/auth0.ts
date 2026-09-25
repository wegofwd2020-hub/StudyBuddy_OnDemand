import { Auth0Client } from "@auth0/nextjs-auth0/server";

let auth0: Auth0Client | null = null;

export function getAuth0() {
  if (!auth0) {
    auth0 = new Auth0Client({
      domain: process.env.AUTH0_DOMAIN,
      clientId: process.env.AUTH0_CLIENT_ID,
      clientSecret: process.env.AUTH0_CLIENT_SECRET,
      secret: process.env.AUTH0_SECRET,
    });
  }
  return auth0;
}
