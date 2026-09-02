/**
 * Reset-password confirmation copy (Venki, 2 Sep):
 *
 *   "Reset password – Email ID entered is not validated. Can it be checked to
 *    see whether it exists before sending the reset password link"
 *
 * The answer to the request as asked is no, and it stays no.
 * `POST /auth/forgot-password` returns 200 whether or not the address is
 * registered; distinguishing them turns the form into an oracle for "does this
 * person have an account here?", which for a product holding minors'
 * educational records is a disclosure. It is listed as a non-negotiable rule in
 * CLAUDE.md, and this file exists so a well-meaning future change to the copy
 * cannot quietly reintroduce the claim that leaks the same fact in words.
 *
 * What WAS wrong is that the guarantee's cost landed on the user. The screen
 * said "Check your email for a reset link" — an unconditional assertion — so a
 * mistyped address sent someone to wait on an inbox that would never receive
 * anything. That is what he was really reporting.
 *
 * Format validation (`z.string().email()`) already ships on the form, which is
 * the half of his request that is safe to grant.
 *
 * Run with:
 *   npm test -- reset-password-non-enumeration
 */

import { describe, it, expect } from "vitest";
import en from "@/i18n/en.json";
import fr from "@/i18n/fr.json";
import es from "@/i18n/es.json";

type Bundle = Record<string, Record<string, string>>;

function stringsOf(bundle: unknown): Record<string, string> {
  for (const block of Object.values(bundle as Bundle)) {
    if (block && typeof block === "object" && "reset_email_sent" in block) {
      return block as Record<string, string>;
    }
  }
  throw new Error("reset_email_sent not found in bundle");
}

const LOCALES: [string, Record<string, string>][] = [
  ["en", stringsOf(en)],
  ["fr", stringsOf(fr)],
  ["es", stringsOf(es)],
];

describe("reset-password confirmation does not claim an email was sent", () => {
  it.each(LOCALES)("%s states the condition rather than asserting delivery", (_l, s) => {
    const sent = s.reset_email_sent;
    expect(sent).toBeTruthy();
    // Conditional in every language we ship: "if" / "si". The point is that the
    // sentence does not promise an email to an address we cannot confirm.
    expect(sent.toLowerCase()).toMatch(/\b(if|si)\b/);
  });

  it.each(LOCALES)("%s does not tell the reader to go check their inbox", (_l, s) => {
    // The old copy — "Check your email for a reset link" — is exactly the
    // assertion that stranded a user who typed the wrong address.
    expect(s.reset_email_sent.toLowerCase()).not.toMatch(
      /^(check your email|revisa tu correo|vérifiez votre e-mail)/,
    );
  });

  it.each(LOCALES)("%s offers a route out when nothing arrives", (_l, s) => {
    // Without this the conditional wording is honest but useless: the reader
    // still cannot tell a slow email from a wrong address, and has nothing to
    // do about either.
    expect(s.reset_email_hint).toBeTruthy();
    expect(s.reset_email_hint.length).toBeGreaterThan(40);
  });

  it("never confirms or denies that an account exists", () => {
    // A future edit reaching for helpfulness ("No account found for that
    // address") would leak in words precisely what the always-200 response
    // exists to withhold.
    const leaking =
      /(no account|not registered|unknown email|doesn't exist|does not exist|no existe|aucun compte)/i;
    for (const [locale, s] of LOCALES) {
      expect(s.reset_email_sent, locale).not.toMatch(leaking);
    }
  });
});
