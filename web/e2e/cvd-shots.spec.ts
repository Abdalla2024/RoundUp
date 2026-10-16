import fs from "node:fs";
import { test, type Page } from "@playwright/test";
// @ts-expect-error plain .mjs helper without types
import { MATRICES } from "../tools/cvd.mjs";

// Colour-blindness check (DESIGN.md §10): the main screens as seen with protanopia, deuteranopia and tritanopia.
// Method: screenshot each screen, then run every pixel through the Machado, Oliveira and Fernandes (2009) matrices at severity 1.0 in
// LINEAR RGB (tools/cvd.mjs has the matrices and the source), inside the browser's canvas. Run: REDESIGN_SHOTS_RUN=1 npx playwright test e2e/cvd-shots.spec.ts
// Output (committed): screenshots/redesign/cvd/<screen>-<theme>-<original|protanopia|deuteranopia|tritanopia>.jpg (900 px wide).
const OUT = "screenshots/redesign/cvd";
test.skip(!process.env.REDESIGN_SHOTS_RUN, "screenshot capture only");

async function simulate(page: Page, png: Buffer, kind: string | null): Promise<Buffer> {
  const url = "data:image/png;base64," + png.toString("base64");
  const out = await page.evaluate(async ([src, m, targetW]) => {
    const img = new Image(); img.src = src as string; await img.decode();
    const w = targetW as number, h = Math.round(img.height * (w / img.width));
    const c = document.createElement("canvas"); c.width = w; c.height = h;
    const g = c.getContext("2d")!; g.imageSmoothingQuality = "high"; g.drawImage(img, 0, 0, w, h);
    if (m) {
      const mat = m as number[][], d = g.getImageData(0, 0, w, h), px = d.data;
      const lin = (v: number) => { v /= 255; return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; };
      const enc = (l: number) => { l = l < 0 ? 0 : l > 1 ? 1 : l; return 255 * (l <= 0.0031308 ? 12.92 * l : 1.055 * l ** (1 / 2.4) - 0.055); };
      for (let i = 0; i < px.length; i += 4) {
        const r = lin(px[i]), gg = lin(px[i + 1]), b = lin(px[i + 2]);
        px[i] = enc(mat[0][0] * r + mat[0][1] * gg + mat[0][2] * b);
        px[i + 1] = enc(mat[1][0] * r + mat[1][1] * gg + mat[1][2] * b);
        px[i + 2] = enc(mat[2][0] * r + mat[2][1] * gg + mat[2][2] * b);
      }
      g.putImageData(d, 0, 0);
    }
    return c.toDataURL("image/jpeg", 0.6).split(",")[1];
  }, [url, kind ? (MATRICES as Record<string, number[][]>)[kind] : null, 900] as const);
  return Buffer.from(out, "base64");
}

for (const theme of ["light", "dark"] as const) {
  test(`colour-blindness simulations (${theme})`, async ({ page, browser }) => {
    test.setTimeout(240_000);
    fs.mkdirSync(OUT, { recursive: true });
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.emulateMedia({ colorScheme: theme });
    const sim = await (await browser.newContext()).newPage();
    const save = async (name: string) => {
      await page.waitForLoadState("networkidle"); await page.mouse.move(0, 0); await page.waitForTimeout(1500);
      const png = await page.screenshot({ fullPage: true });
      for (const kind of [null, "protanopia", "deuteranopia", "tritanopia"] as const) {
        fs.writeFileSync(`${OUT}/${name}-${theme}-${kind ?? "original"}.jpg`, await simulate(sim, png, kind));
      }
    };
    await page.goto("/");
    await page.locator(".scenario .spark").first().waitFor();
    await save("setup");
    // a gain (the default made-up run) and a loss (the crash scenario ending inside the fall)
    await page.getByRole("radio", { name: /Crash and recovery/ }).check();
    await page.getByRole("button", { name: "Run simulation" }).click();
    await page.waitForURL("**/results"); await page.getByText("In this made-up scenario").waitFor();
    await save("results-gain");
    await page.goto("/");
    await page.getByRole("radio", { name: /Crash and recovery/ }).check();
    await page.getByLabel("Start date").fill("2015-01-02"); await page.getByLabel("End date").fill("2016-11-30");
    await page.getByRole("button", { name: "Run simulation" }).click();
    await page.waitForURL("**/results"); await page.getByText("In this made-up scenario").waitFor();
    await save("results-loss");
    await page.getByRole("link", { name: "Compare with another way of investing" }).click();
    await page.getByRole("button", { name: "Compare" }).click();
    await page.getByRole("rowheader", { name: "Growth on round-ups" }).waitFor();
    await save("compare");
  });
}
