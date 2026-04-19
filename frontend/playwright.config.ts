import { defineConfig, devices } from "@playwright/test";

// Smoke tests run against the live deployment by default so we catch regressions
// only visible end-to-end (CSS hydration bugs, CDN caching weirdness, RSS
// sources dying). Override with `PLAYWRIGHT_BASE_URL` for local testing.
export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 30_000,
  expect: { timeout: 8_000 },
  fullyParallel: true,
  retries: process.env.CI ? 2 : 0,
  reporter: [["list"]],
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "https://predictor.nullshift.sh",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  ],
});
