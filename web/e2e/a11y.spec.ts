import fs from "node:fs";
import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import { runSample, signIn } from "./helpers";

// Every screen in light, dark and mobile: zero axe violations (WCAG 2.0/2.1/2.2 A and AA, plus best practice).
const MODES = {
  light: { viewport: { width: 1280, height: 900 }, colorScheme: "light" as const },
  dark: { viewport: { width: 1280, height: 900 }, colorScheme: "dark" as const },
  mobile: { viewport: { width: 390, height: 844 }, colorScheme: "light" as const, isMobile: true, hasTouch: true, deviceScaleFactor: 2 },
};
const report: Record<string, unknown> = {};

async function check(page: Page, name: string, mode: string) {
  await page.waitForLoadState("networkidle");
  const res = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa", "best-practice"]).analyze();
  const v = res.violations.map((x) => ({ id: x.id, impact: x.impact, nodes: x.nodes.length, help: x.help,
    targets: x.nodes.slice(0, 3).map((n) => n.target.join(" ")) }));
  report[`${name}/${mode}`] = { violations: v, passes: res.passes.length };
  await page.screenshot({ path: `screenshots/${name}-${mode}.png`, fullPage: true });
  expect(v, `${name}/${mode}`).toEqual([]);
}

for (const [mode, opts] of Object.entries(MODES)) {
  test.describe(mode, () => {
    test.use(opts);
    test(`setup, results, compare (${mode})`, async ({ page }) => {
      await page.goto("/");
      await check(page, "setup", mode);
      await runSample(page);
      await check(page, "results", mode);
      await page.getByRole("link", { name: "Compare with another way of investing" }).click();
      await page.getByRole("button", { name: "Compare" }).click();
      await page.getByRole("rowheader", { name: "Growth on round-ups" }).waitFor();
      await check(page, "compare", mode);
    });
    test(`saved: signed out, empty, with a scenario (${mode})`, async ({ page }) => {
      await page.goto("/saved");
      await page.getByLabel("Email").waitFor();
      await check(page, "saved-signed-out", mode);
      await runSample(page);
      await signIn(page, `a11y-${mode}@example.test`);
      await page.getByRole("heading", { name: "Nothing saved yet" }).waitFor();
      await check(page, "saved-empty", mode);
      await page.goBack();
      await page.getByRole("button", { name: "Save this scenario" }).click();
      await page.getByLabel("Name for this scenario").fill(`Crash test (${mode})`);
      await page.getByRole("button", { name: "Save", exact: true }).click();
      await page.getByRole("link", { name: "See saved scenarios" }).click();
      await page.getByRole("heading", { name: `Crash test (${mode})` }).waitFor();
      await check(page, "saved-list", mode);
    });
    test(`how this works and privacy (${mode})`, async ({ page }) => {
      await page.goto("/how"); await check(page, "how", mode);
      await page.goto("/privacy"); await check(page, "privacy", mode);
    });
  });
}

test.afterAll(() => {
  const file = "screenshots/axe-report.json";
  const prev = fs.existsSync(file) ? JSON.parse(fs.readFileSync(file, "utf8")) : {};
  fs.writeFileSync(file, JSON.stringify({ ...prev, ...report }, null, 1));
});
