import fs from "node:fs";
import { expect, test } from "@playwright/test";
import { API, runSample } from "./helpers";

// Page weight (bytes the browser downloads per page) and API response size for a full-range run.
test("page weight and response sizes", async ({ page, request }) => {
  const out: Record<string, unknown> = {};
  const bytes: Record<string, number> = {}; let total = 0; let wire = 0;
  page.on("response", async (r) => {
    try {
      const b = (await r.body()).length;                       // uncompressed
      const type = r.request().resourceType();
      bytes[type] = (bytes[type] ?? 0) + b; total += b;
      wire += (await r.request().sizes()).responseBodySize;    // bytes actually transferred (compressed)
    } catch { /* redirects have no body */ }
  });
  const t0 = Date.now();
  await page.goto("/", { waitUntil: "networkidle" });
  out.setup_first_load = { ms: Date.now() - t0, total_bytes: total, transferred_bytes: wire, by_type: { ...bytes } };

  const full = { scenario_id: "crash-and-recovery", style: "broad", start: "2012-01-03", end: "2026-09-30",
    generate: { seed: 42, max_per_day: 3 }, strategy: "next_session", reinvest: true };
  for (const buys of ["none", "all"] as const) {
    const t = Date.now();
    const r = await request.post(`${API}/v1/simulate`, { data: { ...full, buys } });
    const body = await r.body();
    out[`api_simulate_full_range_buys_${buys}`] = { status: r.status(), bytes: body.length, ms: Date.now() - t,
      series_points: JSON.parse(body.toString()).result.series.length };
  }
  const tc = Date.now();
  const rc = await request.post(`${API}/v1/compare`, { data: { ...full, strategy: undefined, reinvest: undefined, buys: "none",
    a: { strategy: "next_session", reinvest: true }, b: { strategy: "monthly", reinvest: false } } });
  out.api_compare_full_range = { status: rc.status(), bytes: (await rc.body()).length, ms: Date.now() - tc };

  total = 0; wire = 0; for (const k of Object.keys(bytes)) delete bytes[k];
  const t1 = Date.now();
  await runSample(page, { start: "2012-01-03", end: "2026-09-30" });
  await page.waitForLoadState("networkidle");
  out.run_full_range_to_results = { ms: Date.now() - t1, total_bytes: total, transferred_bytes: wire, by_type: { ...bytes } };
  fs.writeFileSync("screenshots/perf-report.json", JSON.stringify(out, null, 1));
  expect((out.api_simulate_full_range_buys_none as { bytes: number }).bytes).toBeLessThan(250_000);
});
