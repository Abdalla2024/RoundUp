import fs from "node:fs";
import path from "node:path";
import { test, type Page } from "@playwright/test";
import { runSample, signIn } from "./helpers";

// Screenshots of every screen and state in light, dark and mobile (the redesign's "after" set), plus each page's accessibility tree as text.
// PNGs go to SHOTS (ignored by git); tools/compress-shots.sh turns them into the committed JPEGs.
const SHOTS = process.env.REDESIGN_SHOTS ?? "screenshots/redesign/png";
const ARIA = "screenshots/redesign/aria";
const SAMPLES = path.resolve(__dirname, "../../samples");
const MODES = {
  light: { viewport: { width: 1280, height: 900 }, colorScheme: "light" as const },
  dark: { viewport: { width: 1280, height: 900 }, colorScheme: "dark" as const },
  mobile: { viewport: { width: 390, height: 844 }, colorScheme: "light" as const, isMobile: true, hasTouch: true, deviceScaleFactor: 2 },
};

for (const [mode, opts] of Object.entries(MODES)) {
  test.describe(mode, () => {
    test.skip(!process.env.REDESIGN_SHOTS_RUN, "screenshot capture only: REDESIGN_SHOTS_RUN=1 npx playwright test e2e/redesign-shots.spec.ts");
    test.use(opts);
    test(`every screen and state (${mode})`, async ({ page }) => {
      test.setTimeout(180_000);
      fs.mkdirSync(SHOTS, { recursive: true }); fs.mkdirSync(ARIA, { recursive: true });
      const shot = async (name: string) => {
        await page.waitForLoadState("networkidle"); await page.mouse.move(0, 0); await page.waitForTimeout(1500);   // the hero number rolls for about a second
        await page.screenshot({ path: `${SHOTS}/${name}-${mode}.png`, fullPage: true });
        if (mode === "light" || mode === "mobile") fs.writeFileSync(`${ARIA}/${name}-${mode}.yml`, await page.locator("body").ariaSnapshot());
      };
      // loading: the scenario cards show skeletons while the API answers
      let release: () => void = () => {};
      const gate = new Promise<void>((r) => { release = r; });
      await page.route("**/v1/scenarios", async (route) => { await gate; await route.continue(); });
      await page.goto("/");
      await page.locator(".skeleton-card").first().waitFor();
      await page.screenshot({ path: `${SHOTS}/setup-loading-${mode}.png`, fullPage: false });
      release();
      await page.locator(".scenario .spark").first().waitFor();
      await page.unroute("**/v1/scenarios");
      await shot("setup");
      if (mode === "mobile") { await page.getByRole("button", { name: "Menu" }).click(); await shot("menu-open"); await page.getByRole("button", { name: "Menu" }).click(); }
      await page.getByText("Adjust the average round-up").click();
      await shot("setup-adjust-open");
      // upload
      await page.getByRole("radio", { name: /Upload a CSV/ }).check();
      await page.getByLabel("CSV file (up to 2 MB)").setInputFiles(path.join(SAMPLES, "sample-transactions.csv"));
      await page.getByLabel("Date column").waitFor();
      await shot("setup-upload-file");
      await page.getByRole("button", { name: "Check this file" }).click();
      await page.locator(".form-error").waitFor();
      await shot("setup-upload-error");
      await page.getByLabel("How are amounts signed?").selectOption("debits_positive");
      await page.getByRole("button", { name: "Check this file" }).click();
      await page.getByRole("status").filter({ hasText: "rows can be used" }).waitFor();
      await shot("setup-upload-checked");
      // an API error on the setup screen: the network fails
      await page.getByRole("radio", { name: /Typical spending/ }).check();
      await page.route("**/v1/simulate", (route) => route.abort());
      await page.getByRole("button", { name: "Run simulation" }).click();
      await page.locator(".form-error").waitFor();
      await shot("setup-network-error");
      await page.unroute("**/v1/simulate");
      // results
      await runSample(page);
      await shot("results");
      // a made-up LOSS (the crash scenario, ending inside the fall): red figures with minus signs and down arrows
      await page.goto("/");
      await page.getByRole("radio", { name: /Crash and recovery/ }).check();
      await page.getByLabel("Start date").fill("2015-01-02"); await page.getByLabel("End date").fill("2016-11-30");
      await page.getByRole("button", { name: "Run simulation" }).click();
      await page.waitForURL("**/results"); await page.getByText("In this made-up scenario").waitFor();
      await shot("results-loss");
      await runSample(page);
      await page.getByRole("button", { name: "Show the chart as a table" }).click();
      await page.locator("details.all-assumptions summary").first().click();
      await shot("results-table-assumptions");
      await page.getByRole("link", { name: "Compare with another way of investing" }).click();
      await shot("compare-before");
      await page.getByRole("button", { name: "Compare" }).click();
      await page.getByRole("rowheader", { name: "Growth on round-ups" }).waitFor();
      await shot("compare");
      // empty and saved states
      await page.goto("/results"); await shot("results-empty");
      await page.goto("/compare"); await shot("compare-empty");
      await page.goto("/saved"); await page.getByLabel("Email").waitFor(); await shot("saved-signed-out");
      await runSample(page);
      await signIn(page, `shots-${mode}@example.test`);
      await page.getByRole("heading", { name: "Nothing saved yet" }).waitFor(); await shot("saved-empty");
      await page.goBack();
      await page.getByRole("button", { name: "Save this scenario" }).click();
      await page.getByLabel("Name for this scenario").fill("Typical week, 10 purchases");
      await shot("results-save-form");
      await page.getByRole("button", { name: "Save", exact: true }).click();
      await page.getByText(/Saved as/).waitFor();
      await page.getByRole("link", { name: "See saved scenarios" }).click();
      await page.getByRole("heading", { name: /Typical week/ }).waitFor(); await shot("saved-list");
      await page.getByRole("button", { name: /^Delete / }).click(); await shot("saved-delete-dialog");
      await page.keyboard.press("Escape");
      await page.goto("/how"); await shot("how");
      await page.goto("/privacy"); await shot("privacy");
      await page.goto("/nothing-here"); await shot("not-found");
    });
  });
}
