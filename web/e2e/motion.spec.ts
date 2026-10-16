import { expect, test, type Page } from "@playwright/test";
import { geometryIssues } from "./geometry";
import { runSample } from "./helpers";

// Motion: smooth in-page scrolling with focus handling, entrance animations, the chart drawing in, and reduced motion.
// Every other spec runs with reduced motion (playwright.config.ts) so layout, axe and screenshots are taken at rest; here each test says which it wants.

/** Waits until nothing is animating or transitioning (so measurements are taken at rest). */
async function settled(page: Page) {
  await page.evaluate(async () => { await Promise.all(document.getAnimations().map((a) => a.finished.catch(() => undefined))); });
  await page.waitForTimeout(100);
}

test.describe("motion on", () => {
  test.use({ reducedMotion: "no-preference" });

  test("clicking a step scrolls smoothly, highlights it at once, lands below the sticky rail, and moves focus to its heading", async ({ page }) => {
    await page.goto("/");
    await page.locator("li[data-state='current']").waitFor();
    const samples = page.evaluate(() => new Promise<number[]>((resolve) => {
      const out: number[] = []; const t0 = performance.now();
      const tick = () => { out.push(Math.round(window.scrollY)); performance.now() - t0 < 1500 ? requestAnimationFrame(tick) : resolve(out); };
      tick();
    }));
    await page.getByRole("link", { name: /Dates/ }).click();
    // highlighted at once (while the page is still scrolling)
    await expect(page.locator(".rail li[data-state='current']")).toContainText("Dates", { timeout: 300 });
    const ys = await samples;
    const final = ys[ys.length - 1];
    expect(final).toBeGreaterThan(300);
    expect(ys.filter((y) => y > 0 && y < final).length, "intermediate scroll positions: a smooth scroll, not a jump").toBeGreaterThanOrEqual(3);
    await expect(page).toHaveURL(/#step-4$/);
    const focus = await page.evaluate(() => ({ cls: document.activeElement?.className, inStep4: Boolean(document.activeElement?.closest("#step-4")) }));
    expect(focus).toEqual({ cls: "step-title", inStep4: true });
    // not hidden under the sticky progress rail
    const rail = (await page.locator(".rail-wrap").boundingBox())!, card = (await page.locator("#step-4").boundingBox())!;
    expect(card.y).toBeGreaterThanOrEqual(rail.y + rail.height - 1);
  });

  test("the hero's 'Start a simulation' link scrolls smoothly to step 1 and focuses its heading; the skip link still jumps natively", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: "Start a simulation" }).click();
    await expect(page).toHaveURL(/#step-1$/);
    await expect.poll(() => page.evaluate(() => document.activeElement?.className)).toBe("step-title");
    await page.goto("/how");
    await page.keyboard.press("Tab");
    await expect(page.getByRole("link", { name: "Skip to main content" })).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(page).toHaveURL(/#main$/);
  });

  test("cards below the fold wait invisible, rise in when scrolled to, and everything ends fully visible at rest", async ({ page }) => {
    await page.goto("/");
    const card = page.locator("#step-4");
    await expect(card).toHaveAttribute("data-reveal", "pending");
    expect(await card.evaluate((e) => getComputedStyle(e).opacity)).toBe("0");
    await card.scrollIntoViewIfNeeded();
    await expect(card).toHaveAttribute("data-reveal", "in");
    await settled(page);
    expect(await card.evaluate((e) => [getComputedStyle(e).opacity, getComputedStyle(e).transform])).toEqual(["1", "none"]);
    // scroll the whole page: nothing is left hidden
    for (let y = 0; y <= 4000; y += 500) { await page.evaluate((v) => window.scrollTo(0, v), y); await page.waitForTimeout(120); }
    await settled(page);
    const hidden = await page.evaluate(() => [...document.querySelectorAll("[data-reveal], [data-draw]")]
      .filter((e) => e.getAttribute("data-reveal") !== "in" && e.getAttribute("data-draw") !== "in").map((e) => e.className));
    expect(hidden).toEqual([]);
  });

  test("a pending card is shown the moment it holds keyboard focus (keyboard users never meet invisible controls)", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("#step-4")).toHaveAttribute("data-reveal", "pending");
    await page.locator("#start").focus();
    expect(await page.locator("#step-4").evaluate((e) => getComputedStyle(e).opacity)).toBe("1");
  });

  test("nothing is clipped or overlapping once the animations have finished", async ({ page }) => {
    await page.goto("/");
    for (let y = 0; y <= 3000; y += 500) { await page.evaluate((v) => window.scrollTo(0, v), y); await page.waitForTimeout(100); }
    await settled(page);
    expect(await geometryIssues(page)).toEqual([]);
    await runSample(page);
    for (let y = 0; y <= 3000; y += 500) { await page.evaluate((v) => window.scrollTo(0, v), y); await page.waitForTimeout(100); }
    await settled(page);
    expect(await geometryIssues(page)).toEqual([]);
  });

  test("the chart draws in once, the first time it is seen, and leaves no clip behind", async ({ page }) => {
    await page.addInitScript(() => {
      (window as never as { __anims: string[] }).__anims = [];
      document.addEventListener("animationstart", (e) => (window as never as { __anims: string[] }).__anims.push((e as AnimationEvent).animationName), true);
    });
    await runSample(page);
    const chart = page.getByTestId("chart").first();
    await chart.scrollIntoViewIfNeeded();
    await expect(chart).toHaveAttribute("data-draw", "in");
    await settled(page);
    const draws = () => page.evaluate(() => (window as never as { __anims: string[] }).__anims.filter((n) => n === "draw").length);
    expect(await draws()).toBe(1);
    expect(await chart.evaluate((e) => getComputedStyle(e).clipPath)).toBe("none");       // nothing left behind to cut the focus ring
    // scrolling away and back does not replay it
    await page.evaluate(() => window.scrollTo(0, 0)); await page.waitForTimeout(300);
    await chart.scrollIntoViewIfNeeded(); await settled(page);
    expect(await draws()).toBe(1);
  });

  test("light and dark ease into each other, then the transition class is removed", async ({ page }) => {
    await page.goto("/");
    await page.locator(".theme-toggle").click();
    expect(await page.evaluate(() => document.documentElement.classList.contains("theme-anim"))).toBe(true);
    await page.waitForTimeout(600);
    expect(await page.evaluate(() => document.documentElement.classList.contains("theme-anim"))).toBe(false);
  });

  test("hover lifts a saved card; pressing a button shrinks it slightly (translate and scale, not the entrance's transform)", async ({ page }) => {
    await runSample(page);
    expect(await page.evaluate(() => getComputedStyle(document.querySelector(".btn-primary")!).transitionProperty)).toContain("scale");
    expect(await page.evaluate(() => getComputedStyle(document.documentElement).scrollBehavior)).toBe("auto");   // JS decides; no global smooth scrolling
  });
});

test.describe("reduced motion", () => {
  test.use({ reducedMotion: "reduce" });

  test("a step link jumps instantly, focuses the heading at once, and nothing is marked for animation", async ({ page }) => {
    await page.goto("/");
    expect(await page.evaluate(() => document.documentElement.getAttribute("data-motion"))).toBeNull();
    expect(await page.locator("[data-reveal], [data-draw]").count()).toBe(0);
    const samples = page.evaluate(() => new Promise<number[]>((resolve) => {
      const out: number[] = []; const t0 = performance.now();
      const tick = () => { out.push(Math.round(window.scrollY)); performance.now() - t0 < 600 ? requestAnimationFrame(tick) : resolve(out); };
      tick();
    }));
    await page.getByRole("link", { name: /Dates/ }).click();
    const ys = await samples;
    const final = ys[ys.length - 1];
    expect(ys.filter((y) => y > 0 && y < final).length, "no in-between positions: an instant jump").toBeLessThanOrEqual(1);
    expect(await page.evaluate(() => document.activeElement?.className)).toBe("step-title");
    await expect(page.locator(".rail li[data-state='current']")).toContainText("Dates");
  });

  test("no animation or transition runs anywhere, and every card is fully visible without scrolling to it", async ({ page }) => {
    await runSample(page);
    expect(await page.evaluate(() => document.getAnimations().length)).toBe(0);
    const opacities = await page.evaluate(() => [...document.querySelectorAll(".stat, .card, .strip, .chart-box")].map((e) => getComputedStyle(e).opacity));
    expect(new Set(opacities)).toEqual(new Set(["1"]));
    expect(await page.evaluate(() => getComputedStyle(document.documentElement).scrollBehavior)).toBe("auto");
    await page.locator(".theme-toggle").click();
    expect(await page.evaluate(() => getComputedStyle(document.body).transitionDuration)).toMatch(/^0s/);
  });
});
