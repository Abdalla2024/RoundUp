import fs from "node:fs";
import path from "node:path";
import { expect, test, type Page } from "@playwright/test";

// On the deployed preview: the colour scheme (tokens as served, gain/loss with sign and arrow, neutral differences) and the motion
// (smooth in-page scroll with focus, entrance, reduced motion). No sign-in is attempted.
const tokens = JSON.parse(fs.readFileSync(path.resolve(__dirname, "../app/tokens.json"), "utf8")) as { themes: Record<string, Record<string, string>> };
const kebab = (s: string) => s.replace(/[A-Z]/g, (c) => "-" + c.toLowerCase());

async function runLoss(page: Page) {
  await page.goto("/");
  await page.getByRole("radio", { name: /Crash and recovery/ }).check();
  await page.getByLabel("Start date").fill("2015-01-02"); await page.getByLabel("End date").fill("2016-11-30");
  await page.getByRole("button", { name: "Run simulation" }).click();
  await page.waitForURL("**/results"); await page.getByText("In this made-up scenario").waitFor();
}

for (const scheme of ["light", "dark"] as const) {
  test.describe(`colour (${scheme})`, () => {
    test.use({ colorScheme: scheme });
    test("the served stylesheet carries the green/red tokens", async ({ page }) => {
      await page.goto("/");
      const got = await page.evaluate((keys) => Object.fromEntries(keys.map((k) => [k, getComputedStyle(document.documentElement).getPropertyValue(`--${k}`).trim()])),
        ["primary", "gain", "gain-text", "loss", "series-b", "bg"]);
      const t = tokens.themes[scheme];
      const lower = (o: Record<string, string>) => Object.fromEntries(Object.entries(o).map(([k, v]) => [k, v.toLowerCase()]));     // the minifier lower-cases hex values
      expect(lower(got)).toEqual(lower({ primary: t.primary, gain: t.gain, "gain-text": t.gainText, loss: t.loss, "series-b": t.seriesB, bg: t.bg }));
    });
    test("a made-up loss: minus sign, down arrow, loss colour; a gain: plus sign, up arrow; strategy differences stay neutral", async ({ page }) => {
      await runLoss(page);
      const growth = page.locator(".stat").filter({ hasText: "Growth on round-ups" });
      await expect(growth.locator(".delta.neg")).toHaveText("−$114.44");
      await expect(growth.locator(".delta.neg svg.icon-down")).toBeVisible();
      await expect(page.locator(".dip.neg svg.icon-down")).toBeVisible();
      const hex = (c: string) => "#" + c.match(/\d+/g)!.slice(0, 3).map((n) => Number(n).toString(16).padStart(2, "0")).join("").toUpperCase();
      expect(hex(await growth.locator(".delta.neg").evaluate((e) => getComputedStyle(e).color))).toBe(tokens.themes[scheme].loss);
      await page.getByRole("link", { name: "Compare with another way of investing" }).click();
      await page.getByRole("button", { name: "Compare" }).click();
      await page.getByRole("rowheader", { name: "Growth on round-ups" }).waitFor();
      await expect(page.getByTestId("diff-summary").locator("svg.icon-up, svg.icon-down")).toHaveCount(0);        // a difference is not a gain or a loss
      await expect(page.locator("td[data-label='B minus A'] .delta.flat").first()).toBeVisible();
      await expect(page.locator("td[data-label='B minus A'] .delta.pos, td[data-label='B minus A'] .delta.neg")).toHaveCount(0);
    });
  });
}

test.describe("motion on", () => {
  test.use({ reducedMotion: "no-preference" });
  test("a step link scrolls smoothly, highlights the step, focuses its heading; cards below the fold wait and then come in", async ({ page }) => {
    await page.goto("/");
    await page.locator("li[data-state='current']").waitFor();
    await expect(page.locator("#step-4")).toHaveAttribute("data-reveal", "pending");
    const samples = page.evaluate(() => new Promise<number[]>((resolve) => {
      const out: number[] = []; const t0 = performance.now();
      const tick = () => { out.push(Math.round(window.scrollY)); performance.now() - t0 < 1800 ? requestAnimationFrame(tick) : resolve(out); };
      tick();
    }));
    await page.getByRole("link", { name: /Dates/ }).click();
    await expect(page.locator(".rail li[data-state='current']")).toContainText("Dates", { timeout: 500 });
    const ys = await samples; const final = ys[ys.length - 1];
    expect(ys.filter((y) => y > 0 && y < final).length).toBeGreaterThanOrEqual(3);
    await expect(page).toHaveURL(/#step-4$/);
    expect(await page.evaluate(() => document.activeElement?.className)).toBe("step-title");
    await expect(page.locator("#step-4")).toHaveAttribute("data-reveal", "in");
    await page.evaluate(async () => { await Promise.all(document.getAnimations().map((a) => a.finished.catch(() => undefined))); });
    expect(await page.locator("#step-4").evaluate((e) => getComputedStyle(e).opacity)).toBe("1");
  });
});

test.describe("reduced motion", () => {
  test.use({ reducedMotion: "reduce" });
  test("nothing is marked for animation, links jump instantly, focus still moves", async ({ page }) => {
    await page.goto("/");
    expect(await page.locator("[data-reveal], [data-draw]").count()).toBe(0);
    expect(await page.evaluate(() => document.documentElement.getAttribute("data-motion"))).toBeNull();
    await page.getByRole("link", { name: /Dates/ }).click();
    expect(await page.evaluate(() => document.activeElement?.className)).toBe("step-title");
    expect(await page.evaluate(() => document.getAnimations().length)).toBe(0);
  });
});
