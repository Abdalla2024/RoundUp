// WCAG 2.x contrast ratios for the design tokens (web/app/tokens.json is the single source; tests/contrast.test.ts enforces them).
import fs from "node:fs";
import path from "node:path";
const lin = (c) => { c /= 255; return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4; };
const lum = (h) => { const n = parseInt(h.slice(1), 16); return 0.2126 * lin(n >> 16) + 0.7152 * lin((n >> 8) & 255) + 0.0722 * lin(n & 255); };
export const ratio = (a, b) => { const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p); return (x + 0.05) / (y + 0.05); };
if (process.argv[1] && process.argv[1].endsWith("contrast.mjs")) {          // run from the web folder: node tools/contrast.mjs
  const tokens = JSON.parse(fs.readFileSync(path.resolve("app/tokens.json"), "utf8"));
  for (const [theme, t] of Object.entries(tokens.themes)) {
    console.log(`\n${theme}`);
    for (const [name, [fg, bg, min]] of Object.entries(tokens.pairs)) {
      const r = ratio(t[fg], t[bg]);
      console.log(`  ${name.padEnd(34)} ${fg}/${bg}  ${r.toFixed(2)}:1  (needs ${min})  ${r >= min ? "ok" : "FAIL"}`);
    }
  }
}
