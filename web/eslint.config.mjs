import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
  ]),
  {
    rules: {
      // This project intentionally calls setState inside useEffect on mount to
      // read localStorage without triggering SSR hydration mismatches. This is
      // the canonical pattern documented in CLAUDE.md ("Hydration rule").
      "react-hooks/set-state-in-effect": "off",
    },
  },
  {
    // #759: no browser-locale date/time formatting outside the single helper
    // module. `toLocaleDateString`/`toLocaleTimeString`/`Intl.DateTimeFormat`
    // render per the VIEWER's OS/browser locale, so the same report reads as
    // a different day to two teachers at the same school depending on their
    // machine's settings — see lib/utils/date.ts for the full rationale.
    // Bare `toLocaleString()` cannot be banned this way: numbers (money,
    // counts) legitimately use it, and a syntax-only selector can't tell a
    // Date receiver from a number receiver.
    files: ["app/**/*.{ts,tsx}", "components/**/*.{ts,tsx}", "lib/**/*.{ts,tsx}"],
    ignores: ["lib/utils/date.ts"],
    rules: {
      "no-restricted-syntax": [
        "error",
        {
          selector: "CallExpression[callee.property.name='toLocaleDateString']",
          message:
            "Use formatDate/formatDateTime from @/lib/utils/date instead of toLocaleDateString() — browser-locale dates read differently per viewer (#759).",
        },
        {
          selector: "CallExpression[callee.property.name='toLocaleTimeString']",
          message:
            "Use formatTime/formatDateTime from @/lib/utils/date instead of toLocaleTimeString() — browser-locale times read differently per viewer (#759).",
        },
        {
          selector:
            "NewExpression[callee.object.name='Intl'][callee.property.name='DateTimeFormat']",
          message:
            "Use the helpers in @/lib/utils/date instead of new Intl.DateTimeFormat() — browser-locale dates read differently per viewer (#759).",
        },
      ],
    },
  },
]);

export default eslintConfig;
