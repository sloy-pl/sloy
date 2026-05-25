import { defineConfig, devices } from "@playwright/test";

/**
 * Visual regression config for the sloy.pl storefront.
 *
 * The site under test is controlled by BASE_URL (defaults to production).
 * Baselines live in tests/__screenshots__/<project>/ and are committed to git.
 *
 *   npm run snapshot   # capture / refresh baselines
 *   npm test           # compare current site against baselines
 *   npm run report     # open the HTML diff report
 */
export default defineConfig({
  testDir: "./tests",
  // Group baselines by viewport project, e.g. tests/__screenshots__/desktop/home.png
  snapshotPathTemplate: "{testDir}/__screenshots__/{projectName}/{arg}{ext}",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  // Retry transient network blips against the live store.
  retries: 2,
  // Serialize requests so we don't trip the storefront's rate limiting.
  workers: 1,
  reporter: [["html", { open: "never" }], ["list"]],
  timeout: 90_000,
  use: {
    baseURL: process.env.BASE_URL ?? "https://sloy.pl",
    locale: "pl-PL",
    timezoneId: "Europe/Warsaw",
    // A real-ish UA avoids bot-detection oddities on the storefront.
    userAgent:
      "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
  },
  expect: {
    toHaveScreenshot: {
      // Tolerate a handful of stray pixels (font hinting, antialiasing).
      maxDiffPixelRatio: 0.01,
      animations: "disabled",
      caret: "hide",
      scale: "css",
    },
  },
  projects: [
    {
      name: "desktop",
      use: { ...devices["Desktop Chrome"], viewport: { width: 1366, height: 900 } },
    },
    {
      name: "mobile",
      use: { ...devices["iPhone 13"] },
    },
  ],
});
