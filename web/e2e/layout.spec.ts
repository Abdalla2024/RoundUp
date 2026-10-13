import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { expect, test, type Page } from "@playwright/test";
import { geometryIssues, type Issue } from "./geometry";
import { runSample } from "./helpers";

// Layout geometry on every screen and state, at seven widths, in light and dark.
// SHOTS lets the same file produce "before" screenshots from the unfixed code.
const SHOTS = process.env.LAYOUT_SHOTS ?? "screenshots/layout";
const WIDTHS = [320, 390, 768, 1024, 1280, 1600, 2000];
const MODES = ["light", "dark"] as const;
const report: Record<string, Issue[]> = {};

// 14 runs x several API calls would trip the API's own rate limit (30 POSTs a minute). Real responses are fetched
// once per distinct request and replayed, so every screen still shows real engine output.
const cache = new Map<string, { status: number; headers: Record<string, string>; body: Buffer }>();
async function replayApi(page: Page) {
  await page.route("**/v1/**", async (route) => {
    const req = route.request();
    if (req.method() === "OPTIONS" || req.url().includes("/v1/saved")) return route.continue();   // saving is the stand-in's job
    const key = `${req.method()} ${req.url()} ${req.postData() ?? ""}`;
    if (!cache.has(key)) {
      const res = await route.fetch();
      cache.set(key, { status: res.status(), headers: res.headers(), body: await res.body() });
    }
    const hit = cache.get(key)!;
    await route.fulfill({ status: hit.status, headers: hit.headers, body: hit.body });
  });
}

// A deliberately awkward file: long column names make the selects as wide as they can get.
const LONG_CSV = "Transaction posting date (UTC),Merchant description as shown by the bank,Amount in account currency (USD),Status\n" +
  "2024-01-02,Corner Coffee,6.16,posted\n2024-01-03,Bakery,64.25,posted\n2024-01-04,Hardware Store,19.00,posted\n";
const SPLIT_CSV = "Date,Description,Money out,Money in\n2024-01-02,Coffee,6.16,\n2024-01-03,Refund,,12.50\n";

async function snap(page: Page, state: string, width: number, mode: string, shot: boolean, opts: { selectValues?: boolean } = {}) {
  if (opts.selectValues === undefined) opts = { selectValues: width >= 360 };
  await page.waitForLoadState("networkidle");
  await page.mouse.move(0, 0);
  const issues = await geometryIssues(page, opts);
  report[`${state} @${width} ${mode}`] = issues;
  if (shot || process.env.LAYOUT_ALL_SHOTS) {
    fs.mkdirSync(SHOTS, { recursive: true });
    await page.screenshot({ path: `${SHOTS}/${state}-${width}-${mode}.png`, fullPage: true });
  }
}

test("the checker itself: it reports planted overlaps, clipping and off-screen boxes", async ({ page }) => {
  await page.setViewportSize({ width: 600, height: 400 });
  await page.setContent(`<style>body{margin:0}.a{position:absolute;left:10px;top:10px;width:120px;height:40px}
    .b{position:absolute;left:60px;top:30px;width:120px;height:40px}
    .c{position:absolute;left:10px;top:120px;width:60px;overflow:hidden;white-space:nowrap}
    .d{position:absolute;left:560px;top:200px;width:120px}
    select{position:absolute;left:10px;top:250px;width:60px}</style>
    <button class="a">First button</button><button class="b">Second button</button>
    <p class="c">A helper sentence that is much too long for this box</p>
    <button class="d">Off the edge</button>
    <select><option>An option that cannot fit in the select</option></select>`);
  const kinds = (await geometryIssues(page)).map((i) => i.kind);
  expect(kinds).toContain("overlap");
  expect(kinds).toContain("clipped");
  expect(kinds).toContain("edge");
  expect((await geometryIssues(page)).some((i) => i.detail.startsWith("select"))).toBe(true);
  await page.setContent(`<button>One</button> <button>Two</button><p>Fine text</p>
    <details><summary>Closed</summary><p>Hidden text that has a box but is not drawn</p></details><p>After</p>`);
  expect(await geometryIssues(page)).toEqual([]);
});

for (const width of WIDTHS) {
  for (const mode of MODES) {
    test(`no overlap, clipping or edge problems at ${width}px (${mode})`, async ({ page }) => {
      test.setTimeout(180_000);
      await page.setViewportSize({ width, height: 900 });
      await page.emulateMedia({ colorScheme: mode });
      await replayApi(page);
      const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "roundup-layout-"));
      const long = path.join(tmp, "long.csv"), split = path.join(tmp, "split.csv"), one = path.join(tmp, "one.csv");
      fs.writeFileSync(long, LONG_CSV); fs.writeFileSync(split, SPLIT_CSV);
      fs.writeFileSync(one, "Date,Amount\n2024-01-02,6.16\n2024-01-03,64.25\n");

      // ---- setup
      const SAMPLES = path.resolve(__dirname, "../../samples");
      const NO_SELECT_VALUES = { selectValues: false };          // 40-character column names cannot fit a phone-width select
      // Below 360 px a long chosen option can be wider than any select can be: the browser shows an ellipsis and the full
      // text is in the list. Overlap, edge and every other check still run there.
      const SELECT_TEXT = { selectValues: width >= 360 };
      await page.goto("/");
      await snap(page, "setup-generate", width, mode, true);
      await page.getByRole("radio", { name: /Upload a CSV/ }).check();
      await snap(page, "setup-upload-before-file", width, mode, true);
      // stress: very long column names (overlap and window-edge checks still apply)
      await page.getByLabel("CSV file (up to 2 MB)").setInputFiles(long);
      await page.getByLabel("Date column").waitFor();
      await snap(page, "setup-upload-long-names", width, mode, true, NO_SELECT_VALUES);
      await page.getByRole("button", { name: "Check this file" }).click();
      await page.locator(".form-error").waitFor();
      await snap(page, "setup-upload-long-names-error", width, mode, true, NO_SELECT_VALUES);
      // realistic: the sample bank exports (full checks, including select text)
      await page.getByLabel("CSV file (up to 2 MB)").setInputFiles(path.join(SAMPLES, "sample-transactions.csv"));
      await page.getByLabel("Date column").waitFor();
      await snap(page, "setup-upload-after-file", width, mode, true);
      await page.getByRole("button", { name: "Check this file" }).click();
      await page.locator(".form-error").waitFor();
      await snap(page, "setup-upload-error", width, mode, true);
      await page.getByLabel("How are amounts signed?").selectOption("debits_positive");
      await page.getByRole("button", { name: "Check this file" }).click();
      await page.getByRole("status").filter({ hasText: "rows can be used" }).waitFor();
      await snap(page, "setup-upload-checked", width, mode, true);
      await page.getByLabel("CSV file (up to 2 MB)").setInputFiles(path.join(SAMPLES, "sample-split-columns.csv"));
      await page.getByLabel("Money out column").waitFor();
      await snap(page, "setup-upload-split-columns", width, mode, true);
      await page.getByLabel("CSV file (up to 2 MB)").setInputFiles(path.join(SAMPLES, "sample-type-column.csv"));
      await page.getByLabel("Debit or credit column").waitFor();
      await snap(page, "setup-upload-type-column", width, mode, true);
      await page.getByLabel("CSV file (up to 2 MB)").setInputFiles(split);
      await page.getByLabel("Money out column").waitFor();
      await snap(page, "setup-upload-split-small", width, mode, false);

      // ---- results and compare
      await runSample(page);
      await snap(page, "results", width, mode, false);
      await page.getByRole("button", { name: "Show the chart as a table" }).click();
      await page.locator("details.all-assumptions summary").first().click();
      await snap(page, "results-table-and-assumptions-open", width, mode, false);
      await page.getByRole("button", { name: "Sign in to save" }).click();
      await page.getByLabel("Email").waitFor();
      await snap(page, "results-signin-open", width, mode, false);
      await page.getByLabel("Email").fill("layout@example.test");
      await page.getByRole("button", { name: "Email me a sign-in link" }).click();
      await page.getByRole("button", { name: "Save this scenario" }).click();
      await snap(page, "results-save-form", width, mode, false);
      await page.getByLabel("Name for this scenario").fill("Layout check");
      await page.getByRole("button", { name: "Save", exact: true }).click();
      await page.getByText(/Saved as/).waitFor();
      await snap(page, "results-saved", width, mode, false);
      await page.getByRole("link", { name: "Compare with another way of investing" }).click();
      await snap(page, "compare-before", width, mode, false);
      await page.getByRole("button", { name: "Compare" }).click();
      await page.getByRole("rowheader", { name: "Growth on round-ups" }).waitFor();
      await snap(page, "compare-after", width, mode, false);

      // ---- saved, how, privacy
      await page.goto("/saved");          // the stand-in session lives in memory, so a full load signs out
      await page.getByLabel("Email").waitFor();
      await snap(page, "saved-signed-out", width, mode, false);
      await page.getByLabel("Email").fill("layout2@example.test");
      await page.getByRole("button", { name: "Email me a sign-in link" }).click();
      await page.getByRole("heading", { name: "Nothing saved yet" }).waitFor();
      await snap(page, "saved-empty", width, mode, false);
      await page.goto("/how"); await snap(page, "how", width, mode, false);
      await page.goto("/privacy"); await snap(page, "privacy", width, mode, false);
      await page.goto("/nothing-here"); await snap(page, "not-found", width, mode, false);

      const bad = Object.entries(report).filter(([k, v]) => k.endsWith(`@${width} ${mode}`) && v.length > 0);
      const summary = bad.map(([k, v]) => `${k}\n   ${v.map((i) => `[${i.kind}] ${i.detail}`).join("\n   ")}`).join("\n");
      expect(bad.length, `layout problems:\n${summary}`).toBe(0);
    });
  }
}

test.afterAll(() => {
  // Merge into the file: Playwright starts a fresh worker after a failing test, which would lose earlier results.
  fs.mkdirSync(SHOTS, { recursive: true });
  const file = `${SHOTS}/geometry-report.json`;
  const prev = fs.existsSync(file) ? JSON.parse(fs.readFileSync(file, "utf8")) : {};
  fs.writeFileSync(file, JSON.stringify({ ...prev, ...report }, null, 1));
});
