// The palette (app/tokens.json) must meet WCAG 2.x contrast in both themes, and app/tokens.css must be generated from it.
import fs from "node:fs";
import path from "node:path";
import { describe, expect, test } from "vitest";
// @ts-expect-error plain .mjs helpers without types
import { ratio } from "../tools/contrast.mjs";
// @ts-expect-error plain .mjs helpers without types
import { dL, deltaE, simulate } from "../tools/cvd.mjs";
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

// Red and green are the pair people with red-green colour blindness confuse most. Meaning never depends on colour alone (a sign and an
// arrow always come with it, tests/screens/design.test.tsx), and the two are also chosen to differ in lightness and to stay apart under
// simulated protanopia, deuteranopia and tritanopia (Machado et al. 2009 matrices, tools/cvd.mjs; WCAG 2.2 SC 1.4.1 allows lightness
// differences of 3:1 as an extra cue, but never as the only one).
describe("gain and loss colours stay apart for colour-blind readers (and differ in lightness)", () => {
  for (const [theme, t] of Object.entries(tokens.themes)) {
    for (const kind of ["protanopia", "deuteranopia", "tritanopia"]) {
      test(`${theme}: small text (gain text vs loss), ${kind}: delta E at least 15`, () => {
        expect(deltaE(simulate(t.gainText, kind), simulate(t.loss, kind))).toBeGreaterThanOrEqual(15);
      });
      test(`${theme}: figures and marks (gain vs loss), ${kind}: delta E at least 20`, () => {
        expect(deltaE(simulate(t.gain, kind), simulate(t.loss, kind))).toBeGreaterThanOrEqual(20);
      });
    }
    test(`${theme}: gain and loss marks differ in lightness (L* by at least 15)`, () => {
      expect(dL(t.gain, t.loss)).toBeGreaterThanOrEqual(15);
    });
    test(`${theme}: strategy B (blue) is not confusable with A (green) under any simulation (delta E at least 20)`, () => {
      for (const kind of ["protanopia", "deuteranopia", "tritanopia"]) {
        expect(deltaE(simulate(t.seriesA, kind), simulate(t.seriesB, kind))).toBeGreaterThanOrEqual(20);
      }
    });
  }
});
