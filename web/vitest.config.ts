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
    testTimeout: 30000,
    hookTimeout: 30000,
    workerTimeout: 60000,
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "."),
    },
  },
});
