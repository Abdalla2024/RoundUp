import { defineConfig, devices } from "@playwright/test";

// Local stand-ins only: no real Supabase project, no real credentials.
const PY = process.env.PYTHON ?? ".venv/bin/python";   // servers start from the repo root (cwd "..")
const WEB = "http://localhost:3100", API = "http://127.0.0.1:8000", STANDIN = "http://127.0.0.1:54321";
const channel = process.env.PW_CHANNEL ?? (process.env.CI ? undefined : "chrome");   // local: installed Chrome

export default defineConfig({
  testDir: "e2e",
  timeout: 60_000,
  fullyParallel: false,
  workers: 1,
  reporter: [["list"]],
  use: { baseURL: WEB, trace: "off", ...(channel ? { channel } : {}) },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"], viewport: { width: 1280, height: 900 }, ...(channel ? { channel } : {}) } },
  ],
  webServer: [
    { command: `${PY} tools/standin/server.py --port 54321 --origin ${WEB}`, cwd: "..", url: `${STANDIN}/auth/v1/.well-known/jwks.json`,
      reuseExistingServer: false, timeout: 30_000 },
    { command: `${PY} -m uvicorn app:app --host 127.0.0.1 --port 8000`, cwd: "..", url: `${API}/v1/health`,
      reuseExistingServer: false, timeout: 60_000,
      env: { SUPABASE_URL: STANDIN, SUPABASE_PUBLISHABLE_KEY: "standin-publishable-key", ALLOWED_ORIGIN: WEB,
             PYTHONPATH: "engine/src:api" } },
    { command: "npm run build && npx next start -p 3100", url: WEB, reuseExistingServer: false, timeout: 300_000,
      env: { NEXT_PUBLIC_API_URL: API, NEXT_PUBLIC_SUPABASE_URL: STANDIN,
             NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY: "standin-publishable-key", NEXT_PUBLIC_AUTH_MODE: "standin" } },
  ],
});
