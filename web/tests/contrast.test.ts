// The palette (app/tokens.json) must meet WCAG 2.x contrast in both themes, and app/tokens.css must be generated from it.
import fs from "node:fs";
import path from "node:path";
import { describe, expect, test } from "vitest";
// @ts-expect-error plain .mjs helpers without types
import { ratio } from "../tools/contrast.mjs";
// @ts-expect-error plain .mjs helpers without types
import { build } from "../tools/gen-tokens-css.mjs";

const root = path.resolve(__dirname, "..");
const tokens = JSON.parse(fs.readFileSync(path.join(root, "app/tokens.json"), "utf8")) as {
  themes: Record<string, Record<string, string>>; pairs: Record<string, [string, string, number]> };

describe("palette contrast (light and dark)", () => {
  for (const [theme, t] of Object.entries(tokens.themes)) {
    for (const [name, [fg, bg, min]] of Object.entries(tokens.pairs)) {
      test(`${theme}: ${name} is at least ${min}:1`, () => {
        expect(ratio(t[fg], t[bg])).toBeGreaterThanOrEqual(min);
      });
    }
  }
  test("both themes define every token", () => {
    expect(Object.keys(tokens.themes.dark).sort()).toEqual(Object.keys(tokens.themes.light).sort());
  });
  test("every colour is a six-digit hex value", () => {
    for (const t of Object.values(tokens.themes)) for (const v of Object.values(t)) expect(v).toMatch(/^#[0-9A-Fa-f]{6}$/);
  });
  test("app/tokens.css is generated from tokens.json (run npm run tokens)", () => {
    expect(fs.readFileSync(path.join(root, "app/tokens.css"), "utf8")).toBe(build());
  });
});
