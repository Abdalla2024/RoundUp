import fs from "node:fs";
import path from "node:path";
import { expect, test, type Page } from "@playwright/test";
import { geometryIssues, type Issue } from "../e2e/geometry";

// From the outside, against the deployed preview: the upload flow with the sample exports, and layout geometry on the CSV step
// at seven widths in light and dark. No sign-in is attempted (that would send an email).
const SAMPLES = path.resolve(__dirname, "../../samples");
const API = process.env.DEPLOY_API!;
const report: Record<string, Issue[]> = {};

for (const [file, convention] of [["sample-transactions.csv", null], ["sample-split-columns.csv", "Money out and money in columns"],
                                  ["sample-type-column.csv", "A column says debit or credit"]] as const) {
  test(`deployed: upload ${file}`, async ({ page }) => {
    await page.goto("/");
    await page.getByRole("radio", { name: /Upload a CSV/ }).check();
    await page.getByLabel("CSV file (up to 2 MB)").setInputFiles(path.join(SAMPLES, file));
    await page.getByLabel("Date column").waitFor();
    const select = page.getByLabel("How are amounts signed?");
    if (convention) await expect(select.locator("option:checked")).toHaveText(convention);
    else {
      await expect(select.locator("option:checked")).toHaveText("Choose how amounts are signed");
      await page.getByRole("button", { name: "Check this file" }).click();
      await expect(page.locator(".form-error")).toContainText("Choose how amounts are signed in this file");
      await select.selectOption("debits_positive");
    }
    await page.getByRole("button", { name: "Check this file" }).click();
    const status = page.getByRole("status").filter({ hasText: "rows can be used" });
    await expect(status).toContainText("93 of 93 rows can be used.");
    await expect(status).toContainText("Pending or cancelled rows: 2.");
    await expect(status).toContainText("Purchases that will add round-ups: 86.");
    await expect(status).toContainText("1 row has a status we don’t recognise.");
    await page.getByLabel("Start date").fill("2024-01-02");
    await page.getByLabel("End date").fill("2024-03-29");
    await page.getByRole("button", { name: "Run simulation" }).click();
    await page.waitForURL("**/results");
    await expect(page.locator(".chips")).toContainText("86 purchases");
    await expect(page.locator("#headline")).toContainText("$38.70");
    await expect(page.getByTestId("not-counted")).toContainText("7 rows add no round-ups");
  });
}

test("deployed: the owner's own export (OWNER_SAMPLE_CSV)", async ({ page }) => {
  const file = process.env.OWNER_SAMPLE_CSV;
  test.skip(!file, "set OWNER_SAMPLE_CSV to run this");
  await page.goto("/");
  await page.getByRole("radio", { name: /Upload a CSV/ }).check();
  await page.getByLabel("CSV file (up to 2 MB)").setInputFiles(file!);
  await page.getByLabel("Date column").waitFor();
  await page.getByLabel("How are amounts signed?").selectOption("debits_positive");
  await page.getByRole("button", { name: "Check this file" }).click();
  await expect(page.getByRole("status").filter({ hasText: "rows can be used" })).toContainText("139 of 139 rows can be used.");
  await page.getByLabel("Start date").fill("2024-01-02");
  await page.getByLabel("End date").fill("2024-03-29");
  await page.getByRole("button", { name: "Run simulation" }).click();
  await page.waitForURL("**/results");
  await expect(page.locator(".chips")).toContainText("136 purchases");
  await expect(page.locator("#headline")).toContainText("$70.90");
});

// parse is limited to 10 a minute per address on the deployed API, so real responses are fetched once and replayed
const cache = new Map<string, { status: number; headers: Record<string, string>; body: Buffer }>();
async function replay(page: Page) {
  await page.route(`${API}/v1/**`, async (route) => {
    const req = route.request();
    if (req.method() === "OPTIONS") return route.continue();
    const key = `${req.method()} ${req.url()} ${req.postData() ?? ""}`;
    if (!cache.has(key)) { const r = await route.fetch(); cache.set(key, { status: r.status(), headers: r.headers(), body: await r.body() }); }
    const hit = cache.get(key)!;
    await route.fulfill({ status: hit.status, headers: hit.headers, body: hit.body });
  });
}
for (const width of [320, 390, 768, 1024, 1280, 1600, 2000]) {
  for (const mode of ["light", "dark"] as const) {
    test(`deployed layout at ${width}px (${mode})`, async ({ page }) => {
      test.setTimeout(120_000);
      await page.setViewportSize({ width, height: 900 });
      await page.emulateMedia({ colorScheme: mode });
      await replay(page);
      const opts = { selectValues: width >= 360 };
      const snap = async (state: string) => { await page.waitForLoadState("networkidle"); report[`${state} @${width} ${mode}`] = await geometryIssues(page, opts); };
      await page.goto("/");
      await page.getByRole("radio", { name: /Upload a CSV/ }).check();
      await page.getByLabel("CSV file (up to 2 MB)").setInputFiles(path.join(SAMPLES, "sample-transactions.csv"));
      await page.getByLabel("Date column").waitFor(); await snap("setup-upload-after-file");
      await page.getByRole("button", { name: "Check this file" }).click();
      await page.locator(".form-error").waitFor(); await snap("setup-upload-error");
      await page.getByLabel("How are amounts signed?").selectOption("debits_positive");
      await page.getByRole("button", { name: "Check this file" }).click();
      await page.getByRole("status").filter({ hasText: "rows can be used" }).waitFor(); await snap("setup-upload-checked");
      await page.getByLabel("CSV file (up to 2 MB)").setInputFiles(path.join(SAMPLES, "sample-split-columns.csv"));
      await page.getByLabel("Money out column").waitFor(); await snap("setup-upload-split-columns");
      await page.goto("/"); await page.getByRole("button", { name: "Run simulation" }).click();
      await page.waitForURL("**/results"); await page.getByText("In this made-up scenario").waitFor(); await snap("results");
      await page.getByRole("link", { name: "Compare with another way of investing" }).click();
      await page.getByRole("button", { name: "Compare" }).click();
      await page.getByRole("rowheader", { name: "Growth on round-ups" }).waitFor(); await snap("compare-after");
      const bad = Object.entries(report).filter(([k, v]) => k.endsWith(`@${width} ${mode}`) && v.length);
      expect(bad.length, bad.map(([k, v]) => `${k}: ${v.map((i) => i.detail).join(" | ")}`).join("\n")).toBe(0);
    });
  }
}

test.afterAll(() => {
  const file = "screenshots/deployed/deployed-layout-report.json";
  const prev = fs.existsSync(file) ? JSON.parse(fs.readFileSync(file, "utf8")) : {};
  fs.writeFileSync(file, JSON.stringify({ ...prev, ...report }, null, 1));
});
