import { defineConfig } from "@playwright/test";

/**
 * ContentForge UI E2E smoke config.
 *
 * Target stack: Vite dev server (port 5173, vite.gate-check.config.ts proxies
 * /api to the contentforge backend on 8099) — both already running on the
 * Hermes host for this board's validation run. Route-hash SPA, no auth.
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 45_000,
  projects: [
    {
      name: "chromium",
      use: { browserName: "chromium" },
    },
  ],
  use: {
    baseURL: "http://127.0.0.1:5173",
    trace: "retain-on-failure",
  },
  reporter: [["list"]],
});
