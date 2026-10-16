import { defineConfig, devices } from "@playwright/test";

// Runs against DEPLOYED previews: no servers are started, no credentials are used, no sign-in is attempted
// (that would send an email). Usage: DEPLOY_WEB=https://... DEPLOY_API=https://... npx playwright test -c playwright.deployed.config.ts
const web = process.env.DEPLOY_WEB;
if (!web || !process.env.DEPLOY_API) throw new Error("Set DEPLOY_WEB and DEPLOY_API to the deployed https addresses.");
const channel = process.env.PW_CHANNEL ?? (process.env.CI ? undefined : "chrome");

export default defineConfig({
  testDir: "e2e-deployed",
  timeout: 90_000,
  workers: 1,
  reporter: [["list"]],
  use: { baseURL: web, trace: "off", reducedMotion: "reduce", ...(channel ? { channel } : {}) },
  projects: [{ name: "deployed", use: { ...devices["Desktop Chrome"], viewport: { width: 1280, height: 900 }, ...(channel ? { channel } : {}) } }],
});
