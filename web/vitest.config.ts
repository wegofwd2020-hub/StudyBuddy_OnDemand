import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: ["./tests/unit/setup.ts"],
    globals: true,
    include: ["tests/unit/**/*.test.{ts,tsx}"],
    exclude: ["tests/e2e/**"],

    // Pin the flags the suite's outcome depends on, so a run means the same
    // thing everywhere it is run.
    //
    // The dev container sets NEXT_PUBLIC_DEMO_MODE=true; CI sets nothing. Demo
    // mode disables controls outright (`disabled={IS_DEMO_MODE || ...}`), so 11
    // tests across digest-page and curriculum-upload-page failed locally and
    // passed in CI, permanently and for no visible reason.
    //
    // That cost a red main on 2026-09-01. A suite that is always red for
    // reasons nobody can explain stops being read, and a genuine failure then
    // hides inside noise that has been written off — which is exactly what
    // happened: a real breakage merged inside a set of failures assumed to be
    // environmental.
    //
    // `false` is the right default because it is what CI and production use;
    // a test that wants demo mode should say so itself by stubbing the module.
    env: {
      NEXT_PUBLIC_DEMO_MODE: "false",
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "."),
    },
  },
});
