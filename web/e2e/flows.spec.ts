import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { expect, test } from "@playwright/test";
import { API, runSample, signIn } from "./helpers";

test("simulate: sample spending → results that match the API exactly", async ({ page, request }) => {
  await runSample(page);
  const api = await (await request.post(`${API}/v1/simulate`, { data: {
    scenario_id: "crash-and-recovery", style: "broad", start: "2015-01-02", end: "2024-12-31",
    generate: { seed: 42, max_per_day: 2 }, strategy: "threshold", reinvest: true, buys: "none" } })).json();
  const s = api.result.summary;
  await expect(page.locator("#headline")).toContainText(`$${Number(s.contributed).toLocaleString("en-US", { minimumFractionDigits: 2 })}`);
  await expect(page.getByRole("note").getByText("Hypothetical simulation on a synthetic market.")).toBeVisible();
  await expect(page.locator(".label-strip").getByText("Synthetic scenario. Not a real fund, not real prices, and not a forecast.")).toBeVisible();
  await expect(page.getByText("Made-up prices.")).toBeVisible();
  await expect(page.getByText(api.result.series_rule)).toBeVisible();
  await expect(page.getByText("Coming later:")).toBeVisible();
});

test("compare: two strategies side by side", async ({ page }) => {
  await runSample(page);
  await page.getByRole("link", { name: "Compare with another way of investing" }).click();
  await page.getByRole("button", { name: "Compare" }).click();
  await expect(page.getByRole("rowheader", { name: "Growth on round-ups" })).toBeVisible();
  await expect(page.getByRole("columnheader", { name: "B minus A" })).toBeVisible();
  await expect(page.getByText("A, lowest point compared with money put in:")).toBeVisible();
});

test("upload a CSV: columns, API check, then results without merchant names", async ({ page }) => {
  const file = path.join(os.tmpdir(), `roundup-e2e-${Date.now()}.csv`);
  fs.writeFileSync(file, "Date,Amount,Description\n2016-03-01,4.37,SECRET CAFE\n2016-03-02,12.10,BOOKS\n" +
    "2016-03-03,-20.00,REFUND\n2016-03-04,512.37,PAYMENT TO CARD\n2016-03-05,7.75,LUNCH\n");
  await page.goto("/");
  await page.getByRole("radio", { name: /Upload a CSV/ }).check();
  await page.getByLabel("CSV file (up to 2 MB)").setInputFiles(file);
  await page.getByLabel("How are amounts signed?").selectOption("debits_positive");
  await page.getByRole("button", { name: "Check this file" }).click();
  await expect(page.getByRole("status")).toContainText("5 of 5 rows can be used.");
  await expect(page.getByRole("status")).toContainText("so no round-ups: 1.");
  await page.getByLabel("Start date").fill("2016-01-04");
  await page.getByLabel("End date").fill("2016-12-30");
  await page.getByRole("button", { name: "Run simulation" }).click();
  await page.waitForURL("**/results");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Your round-ups in a made-up market");
  await expect(page.locator("#headline")).toContainText("$1.78");          // 0.63 + 0.90 + 0.25 (4.37, 12.10, 7.75)
  await expect(page.locator("body")).not.toContainText("SECRET CAFE");
  fs.unlinkSync(file);
});

test("sign in (stand-in) and save; the saved list shows it; delete asks first", async ({ page }) => {
  await runSample(page);
  await signIn(page);
  await page.goBack();                                     // back to results (state kept in memory)
  await page.waitForURL("**/results");
  await page.getByRole("button", { name: "Save this scenario" }).click();
  await page.getByLabel("Name for this scenario").fill("E2E crash test");
  await page.getByRole("button", { name: "Save", exact: true }).click();
  await expect(page.getByRole("status")).toContainText("Saved as “E2E crash test”");
  await page.getByRole("link", { name: "See saved scenarios" }).click();
  await expect(page.getByRole("heading", { name: "E2E crash test" })).toBeVisible();
  await page.getByRole("button", { name: "Delete E2E crash test" }).click();
  await expect(page.getByText(/This removes the scenario and its results/)).toBeVisible();
  await page.getByRole("button", { name: "Delete", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Nothing saved yet" })).toBeVisible();
});

test("another user cannot see the first user's saved scenario (stand-in isolation)", async ({ browser }) => {
  const a = await browser.newPage(); const b = await browser.newPage();
  await runSample(a); await signIn(a, "alice@example.test"); await a.goBack();
  await a.getByRole("button", { name: "Save this scenario" }).click();
  await a.getByLabel("Name for this scenario").fill("Alice only");
  await a.getByRole("button", { name: "Save", exact: true }).click();
  await expect(a.getByRole("status")).toContainText("Saved as");
  await b.goto("/saved"); await b.getByLabel("Email").fill("bob@example.test");
  await b.getByRole("button", { name: "Email me a sign-in link" }).click();
  await expect(b.getByRole("heading", { name: "Nothing saved yet" })).toBeVisible();
  await expect(b.locator("body")).not.toContainText("Alice only");
});

test("API errors reach the user in plain language", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Start date").fill("2011-01-03");
  await page.getByRole("button", { name: "Run simulation" }).click();
  await expect(page.locator(".form-error")).toContainText("The dates must be inside the scenario");   // Next's route announcer is also role=alert
});
