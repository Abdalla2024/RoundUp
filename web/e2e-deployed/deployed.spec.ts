import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import { geometryIssues } from "../e2e/geometry";

const WEB = process.env.DEPLOY_WEB!, API = process.env.DEPLOY_API!;
const report: Record<string, unknown> = {};

async function runSample(page: Page, opts: { start?: string; end?: string } = {}) {
  await page.goto("/");
  await page.getByRole("radio", { name: /Crash and recovery/ }).check();
  if (opts.start) await page.getByLabel("Start date").fill(opts.start);
  if (opts.end) await page.getByLabel("End date").fill(opts.end);
  await page.getByRole("button", { name: "Run simulation" }).click();
  await page.waitForURL("**/results");
  await page.getByText("In this made-up scenario").waitFor();
}

test("smoke: simulate, compare, upload a CSV, saved page signed out (no sign-in attempted)", async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on("console", (m) => { if (m.type() === "error") consoleErrors.push(m.text()); });
  await runSample(page);
  await expect(page.locator(".label-strip")).toContainText("Synthetic scenario. Not a real fund");
  await expect(page.getByText("Made-up prices.")).toBeVisible();
  await expect(page.locator(".recharts-wrapper").first()).toBeVisible();
  await expect(page.locator("body")).not.toContainText(/\d%\s+compared with/);      // owner decision: no percentage
  await page.getByRole("link", { name: "Compare with another way of investing" }).click();
  await page.getByRole("button", { name: "Compare" }).click();
  await expect(page.getByRole("rowheader", { name: "Growth on round-ups" })).toBeVisible();

  const file = path.join(os.tmpdir(), `roundup-deployed-${Date.now()}.csv`);
  fs.writeFileSync(file, "Date,Amount,Description\n2016-03-01,4.37,SECRET CAFE\n2016-03-02,12.10,BOOKS\n2016-03-03,-20.00,REFUND\n");
  await page.goto("/");
  await page.getByRole("radio", { name: /Upload a CSV/ }).check();
  await page.getByLabel("CSV file (up to 2 MB)").setInputFiles(file);
  await page.getByLabel("How are amounts signed?").selectOption("debits_positive");
  await page.getByRole("button", { name: "Check this file" }).click();
  await expect(page.getByRole("status")).toContainText("3 of 3 rows can be used.");
  await page.getByLabel("Start date").fill("2016-01-04"); await page.getByLabel("End date").fill("2016-12-30");
  await page.getByRole("button", { name: "Run simulation" }).click();
  await page.waitForURL("**/results");
  await expect(page.locator("#headline")).toContainText("$1.53");
  await expect(page.locator("body")).not.toContainText("SECRET CAFE");
  fs.unlinkSync(file);

  await page.goto("/saved");
  await expect(page.getByRole("heading", { name: "Sign in to see saved scenarios" })).toBeVisible();   // not submitted
  // vercel.live is Vercel's own preview-feedback toolbar, which exists only on previews; our CSP rightly blocks it.
  expect(consoleErrors.filter((e) => !/vercel\.live/.test(e))).toEqual([]);
});

test("the deployed build points at the right services (no localhost, no stand-in)", async ({ page }) => {
  const urls = new Set<string>();
  page.on("response", (r) => { if (r.url().includes("/_next/static/") && r.url().endsWith(".js")) urls.add(r.url()); });
  await page.goto("/"); await page.waitForLoadState("networkidle");
  const js = (await Promise.all([...urls].map(async (u) => (await page.request.get(u)).text()))).join("\n");
  expect(js).toContain(API);
  expect(js).not.toContain("127.0.0.1:8000");        // the app's local fallback API address (supabase-js itself mentions localhost)
  expect(js).not.toContain("NEXT_PUBLIC_AUTH_MODE");
  expect(js).not.toMatch(/\/standin\/token/);         // the test sign-in stand-in must not be in a deployed build
  expect(js).toContain("rauwjvyaluuxivnktxtk.supabase.co");
});

const MODES = {
  light: { viewport: { width: 1280, height: 900 }, colorScheme: "light" as const },
  dark: { viewport: { width: 1280, height: 900 }, colorScheme: "dark" as const },
  mobile: { viewport: { width: 390, height: 844 }, colorScheme: "light" as const, isMobile: true, hasTouch: true, deviceScaleFactor: 2 },
};
async function check(page: Page, name: string, mode: string) {
  await page.waitForLoadState("networkidle");
  await page.mouse.move(0, 0);
  const res = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa", "best-practice"]).analyze();
  const v = res.violations.map((x) => ({ id: x.id, impact: x.impact, nodes: x.nodes.length, help: x.help }));
  report[`${name}/${mode}`] = { violations: v, passes: res.passes.length };
  await page.screenshot({ path: `screenshots/deployed/${name}-${mode}.png`, fullPage: true });
  expect(v, `${name}/${mode}`).toEqual([]);
}
for (const [mode, opts] of Object.entries(MODES)) {
  test.describe(mode, () => {
    test.use(opts);
    test(`axe on the deployed screens (${mode})`, async ({ page }) => {
      await page.goto("/"); await check(page, "setup", mode);
      await runSample(page); await check(page, "results", mode);
      await page.getByRole("link", { name: "Compare with another way of investing" }).click();
      await page.getByRole("button", { name: "Compare" }).click();
      await page.getByRole("rowheader", { name: "Growth on round-ups" }).waitFor();
      await check(page, "compare", mode);
      await page.goto("/saved"); await page.getByLabel("Email").waitFor(); await check(page, "saved-signed-out", mode);
      await page.goto("/how"); await check(page, "how", mode);
      await page.goto("/privacy"); await check(page, "privacy", mode);
    });
  });
}

test("page weight and response sizes on Vercel", async ({ page, request }) => {
  const out: Record<string, unknown> = {};
  const bytes: Record<string, number> = {}; let total = 0; let wire = 0;
  page.on("response", async (r) => {
    try {
      const b = (await r.body()).length; const type = r.request().resourceType();
      bytes[type] = (bytes[type] ?? 0) + b; total += b; wire += (await r.request().sizes()).responseBodySize;
    } catch { /* no body */ }
  });
  const t0 = Date.now();
  await page.goto("/", { waitUntil: "networkidle" });
  out.setup_first_load = { ms: Date.now() - t0, total_bytes: total, transferred_bytes: wire, by_type: { ...bytes } };
  const full = { scenario_id: "crash-and-recovery", style: "broad", start: "2012-01-03", end: "2026-09-30",
    typical: { per_week: 20, average_roundup: "0.50" }, strategy: "next_session", reinvest: true };
  for (const buys of ["none", "all"] as const) {
    const runs: number[] = []; let size = 0, points = 0;
    for (let i = 0; i < 5; i++) {
      const t = Date.now();
      const r = await request.post(`${API}/v1/simulate`, { data: { ...full, buys } });
      const body = await r.body(); runs.push(Date.now() - t); size = body.length;
      points = JSON.parse(body.toString()).result.series.length;
      expect(r.status()).toBe(200);
    }
    out[`api_simulate_full_range_buys_${buys}`] = { bytes: size, ms_each_of_5: runs, series_points: points };
  }
  const cruns: number[] = []; let csize = 0;
  for (let i = 0; i < 5; i++) {
    const t = Date.now();
    const rc = await request.post(`${API}/v1/compare`, { data: { ...full, strategy: undefined, reinvest: undefined, buys: "none",
      a: { strategy: "next_session", reinvest: true }, b: { strategy: "monthly", reinvest: false } } });
    csize = (await rc.body()).length; cruns.push(Date.now() - t); expect(rc.status()).toBe(200);
  }
  out.api_compare_full_range = { bytes: csize, ms_each_of_5: cruns };
  total = 0; wire = 0; for (const k of Object.keys(bytes)) delete bytes[k];
  const t1 = Date.now();
  await runSample(page, { start: "2012-01-03", end: "2026-09-30" });
  await page.waitForLoadState("networkidle");
  out.run_full_range_to_results = { ms: Date.now() - t1, total_bytes: total, transferred_bytes: wire, by_type: { ...bytes } };
  report.perf = out;
  expect((out.api_simulate_full_range_buys_none as { bytes: number }).bytes).toBeLessThan(250_000);
});

test.afterAll(() => fs.writeFileSync("screenshots/deployed/deployed-report.json", JSON.stringify(report, null, 1)));

test("typical spending on the deployed preview: 10 a week at $0.50 for a whole number of weeks gives purchases x $0.50", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("radio", { name: /Typical spending/ }).check();
  await page.locator("#perweek").fill("10");
  await page.getByLabel("Start date").fill("2016-01-04");          // a Monday
  await page.getByLabel("End date").fill("2016-12-25");           // a Sunday: 51 whole weeks
  await page.getByRole("button", { name: "Run simulation" }).click();
  await page.waitForURL("**/results");
  await page.getByText("In this made-up scenario").waitFor();
  const text = (await page.locator("body").innerText()).replace(/\s+/g, " ");
  expect(text).toContain("Estimate: 10 purchases a week, each with a round-up of $0.50. Real spending varies.");
  expect(text).toContain("510 sample purchases");                 // 51 weeks x 10
  expect(text).toContain("$255.00");                               // 510 x $0.50, the engine's figure shown as sent
});

for (const [mode, opts] of Object.entries(MODES)) {
  test.describe(`geometry ${mode}`, () => {
    test.use(opts);
    test(`no overlap, clipping or edge problems on the deployed screens (${mode})`, async ({ page }) => {
      const problems: string[] = [];
      const look = async (name: string) => { await page.waitForLoadState("networkidle"); await page.waitForTimeout(1500);
        for (const i of await geometryIssues(page)) problems.push(`${name}/${mode}: ${i.kind}: ${i.detail}`); };
      await page.goto("/"); await look("setup");
      await runSample(page); await look("results");
      await page.getByRole("link", { name: "Compare with another way of investing" }).click();
      await page.getByRole("button", { name: "Compare" }).click();
      await page.getByRole("rowheader", { name: "Growth on round-ups" }).waitFor(); await look("compare");
      await page.goto("/saved"); await look("saved");
      await page.goto("/how"); await look("how");
      await page.goto("/privacy"); await look("privacy");
      expect(problems).toEqual([]);
    });
  });
}
