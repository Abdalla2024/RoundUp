import fs from "node:fs";
import { expect, test, type Page } from "@playwright/test";

// Keyboard only: no mouse clicks in this file.
const report: Record<string, unknown> = {};
async function focused(page: Page) {
  return page.evaluate(() => {
    const e = document.activeElement as HTMLElement;
    const ring = (el: Element) => { const cs = getComputedStyle(el);
      return (cs.outlineStyle !== "none" && parseFloat(cs.outlineWidth) >= 2) || cs.boxShadow !== "none"; };
    // radio/checkbox cards draw the focus ring on the surrounding card (.option:has(input:focus-visible))
    const card = e.closest(".option, .switch");
    const label = e.id ? document.querySelector(`label[for="${e.id}"]`)?.textContent : null;
    return { tag: e.tagName.toLowerCase(),
      text: (e.getAttribute("aria-label") || label || e.textContent || (e as HTMLInputElement).value || "").trim().slice(0, 50),
      visibleFocus: ring(e) || (card ? ring(card) : false) };
  });
}
async function tabTo(page: Page, re: RegExp, max = 80) {
  const stops = [];
  for (let i = 0; i < max; i++) {
    await page.keyboard.press("Tab");
    const f = await focused(page);
    stops.push(f);
    if (re.test(f.text)) return stops;
  }
  throw new Error(`never reached ${re} by Tab; stops: ${stops.map((s) => s.text).join(" | ")}`);
}

test("keyboard only: skip link, setup, results, chart, definitions, compare", async ({ page }) => {
  await page.goto("/");
  await page.keyboard.press("Tab");
  expect((await focused(page)).text).toBe("Skip to main content");
  await page.keyboard.press("Enter");
  expect(await page.evaluate(() => document.activeElement?.id)).toBe("main");

  const setupStops = await tabTo(page, /^Run simulation$/);
  report.setup_tab_stops_to_run = setupStops.length;
  expect(setupStops.filter((s) => !s.visibleFocus)).toEqual([]);
  // radio groups are single tab stops; arrow keys change the choice
  await page.keyboard.press("Enter");
  await page.waitForURL("**/results");
  await page.getByText("In this made-up scenario").waitFor();

  await page.locator(".recharts-wrapper").first().waitFor();   // the chart is lazy-loaded; wait until it is drawn
  const toTile = await tabTo(page, /^Growth on round-ups$/);
  await page.keyboard.press("Enter");
  await expect(page.getByText(/How far the value at the end is above, or below/)).toBeVisible();
  expect(toTile.filter((s) => !s.visibleFocus)).toEqual([]);

  const toChart = await tabTo(page, /^Value over time\./, 20);     // the chart is one tab stop (role=group)
  report.chart_reached_by_tab = toChart.length;
  const readout = page.getByTestId("chart-readout").first();
  await expect(readout).toHaveText("");                             // reviewer M6: nothing shown until asked
  await page.keyboard.press("ArrowRight");
  await expect(readout).toContainText(/^Jan 2, 2015: value \$/);
  await page.keyboard.press("End");
  await expect(readout).toContainText(/^Dec 31, 2024: value \$/);
  await page.keyboard.press("Home");
  await expect(readout).toContainText(/^Jan 2, 2015/);
  await page.keyboard.press("PageDown");
  await expect(readout).not.toContainText(/^Jan 2, 2015/);
  report.chart_keys = ["ArrowRight", "End", "Home", "PageDown"];

  await tabTo(page, /^Show the chart as a table$/);
  await page.keyboard.press("Enter");
  await expect(page.getByRole("region", { name: "Value over time as a table" })).toBeVisible();

  await tabTo(page, /^All assumptions \(12\)$/, 120).catch(async () => {
    // on narrow screens the key points come first; on desktop they are after the main column
  });
  await tabTo(page, /^Compare with another way of investing$/, 120);
  await page.keyboard.press("Enter");
  await page.waitForURL("**/compare");
  await tabTo(page, /^Compare$/);
  await page.keyboard.press("Enter");
  await expect(page.getByRole("rowheader", { name: "Growth on round-ups" })).toBeVisible();
});

test("keyboard only: sign in, save, delete dialog closes with Escape", async ({ page }) => {
  await page.goto("/");
  await tabTo(page, /^Run simulation$/);
  await page.keyboard.press("Enter");
  await page.waitForURL("**/results");
  await page.getByText("In this made-up scenario").waitFor();
  await tabTo(page, /^Sign in to save$/, 120);
  await page.keyboard.press("Enter");
  expect((await focused(page)).text).toBe("Email");     // the sign-in form opens in place, focused (reviewer M7)
  await page.keyboard.type("keys@example.test");
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/results$/);
  await tabTo(page, /^Save this scenario$/, 120);
  await page.keyboard.press("Enter");
  await page.keyboard.type("Keyboard save");
  await page.keyboard.press("Enter");
  await expect(page.getByRole("status")).toContainText("Saved as");
  await tabTo(page, /^See saved scenarios$/, 40);
  await page.keyboard.press("Enter");
  await tabTo(page, /^Delete Keyboard save$/, 40);
  await page.keyboard.press("Enter");
  await expect(page.getByRole("dialog")).toBeVisible();
  expect((await focused(page)).text).toBe("Keep it");      // the safe choice has focus
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toBeHidden();
  await expect(page.getByRole("heading", { name: "Keyboard save" })).toBeVisible();
});

test.afterAll(() => fs.writeFileSync("screenshots/keyboard-report.json", JSON.stringify(report, null, 1)));
