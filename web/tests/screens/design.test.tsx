// The redesign's building blocks (stage 6): digit-roll figures, the composition strip, sparklines, the theme toggle, the progress rail,
// skeletons, and the stylesheet's rules (tokens only, reduced motion).
import fs from "node:fs";
import path from "node:path";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";
import { CompositionStrip } from "@/components/ResultParts";
import { Icon } from "@/components/Icon";
import { Num } from "@/components/Num";
import { ProgressRail } from "@/components/ProgressRail";
import { SetupForm } from "@/components/SetupForm";
import { Sparkline } from "@/components/Sparkline";
import { ThemeToggle } from "@/components/ThemeToggle";
import type { Result } from "@/lib/types";
import scenarios from "../fixtures/scenarios.json";
import simulate from "../fixtures/simulate.json";
import { renderWith } from "../helpers";

vi.mock("@/lib/api", async (orig) => ({ ...(await orig<typeof import("@/lib/api")>()),
  api: { scenarios: () => Promise.resolve(scenarios), assumptions: () => Promise.resolve({ disclaimer: "", assumptions: [] }) } }));
const result = simulate.response.result as unknown as Result;
const css = fs.readFileSync(path.resolve(__dirname, "../../app/globals.css"), "utf8");

describe("Num: a money figure drawn as rolling digits, with no arithmetic", () => {
  test("the page holds the engine's text exactly once; the animated copy is hidden from screen readers", () => {
    const { container } = render(<Num text="$4,295.37" />);
    expect(container.textContent).toBe("$4,295.37");                              // nothing but the real figure is in the text
    expect(container.querySelector(".visually-hidden")?.textContent).toBe("$4,295.37");
    const visual = container.querySelector(".num-visual")!;
    expect(visual.getAttribute("aria-hidden")).toBe("true");
    const digits = [...visual.querySelectorAll(".roll")].map((e) => (e as HTMLElement).style.getPropertyValue("--d"));
    expect(digits).toEqual(["4", "2", "9", "5", "3", "7"]);                       // each window shows the digit the engine sent
    expect([...visual.querySelectorAll(".sym")].map((e) => e.getAttribute("data-c"))).toEqual(["$", ",", "."]);
  });
  test("a negative figure keeps its minus sign", () => {
    const { container } = render(<Num text="−$91.91" />);
    expect(container.textContent).toBe("−$91.91");
  });
});

describe("Composition strip (R-13.4)", () => {
  test("widths are the engine's basis points, labels and amounts are its strings", () => {
    const { container } = render(<CompositionStrip result={result} />);
    const comp = result.summary.composition!;
    const segs = [...container.querySelectorAll(".seg")] as HTMLElement[];
    expect(segs.map((s) => s.style.flexGrow)).toEqual(comp.filter((p) => p.share_bp > 0).map((p) => String(p.share_bp)));
    expect(container.querySelector(".strip-legend")!.textContent).toContain(`$${comp[0].amount.replace(/\B(?=(\d{3})+(?!\d))/g, ",")}`);
    expect(screen.getByRole("img", { name: /What the end value is made of: Invested in shares/ })).toBeTruthy();
  });
  test("parts of $0.00 are left out, and an empty result draws nothing", () => {
    const { container } = render(<CompositionStrip result={result} />);
    expect(container.textContent).not.toContain("Dividends kept as cash");
    const none = { ...result, summary: { ...result.summary, composition: result.summary.composition!.map((p) => ({ ...p, amount: "0.00", share_bp: 0 })) } };
    const empty = render(<CompositionStrip result={none} />);
    expect(empty.container.querySelector(".strip")).toBeNull();
  });
});

describe("Sparkline and icons are decoration", () => {
  test("a sparkline is hidden from screen readers and draws one point per number", () => {
    const { container } = render(<Sparkline shape={[0, 50, 100, 25]} />);
    const svg = container.querySelector("svg")!;
    expect(svg.getAttribute("aria-hidden")).toBe("true");
    expect(svg.querySelector("polyline")!.getAttribute("points")!.split(" ")).toHaveLength(4);
  });
  test("icons are aria-hidden and not focusable", () => {
    const { container } = render(<Icon name="coins" />);
    expect(container.querySelector("svg")!.getAttribute("aria-hidden")).toBe("true");
    expect(container.querySelector("svg")!.getAttribute("focusable")).toBe("false");
  });
});

describe("Theme toggle", () => {
  beforeEach(() => { document.documentElement.removeAttribute("data-theme"); localStorage.clear(); });
  test("follows the system until chosen; cycles light, dark, system; remembers the choice; the label says what it will do", () => {
    render(<ThemeToggle />);
    const btn = () => screen.getByRole("button");
    expect(btn().getAttribute("aria-label")).toBe("Colour theme: the system setting. Change to light.");
    expect(document.documentElement.hasAttribute("data-theme")).toBe(false);
    fireEvent.click(btn());
    expect(document.documentElement.getAttribute("data-theme")).toBe("light");
    expect(localStorage.getItem("roundup-theme")).toBe("light");
    expect(btn().getAttribute("aria-label")).toBe("Colour theme: light. Change to dark.");
    fireEvent.click(btn());
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
    fireEvent.click(btn());
    expect(document.documentElement.hasAttribute("data-theme")).toBe(false);          // back to the system setting
    expect(localStorage.getItem("roundup-theme")).toBeNull();
  });
  test("blocked storage does not break it", () => {
    const spy = vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => { throw new Error("blocked"); });
    render(<ThemeToggle />);
    expect(() => fireEvent.click(screen.getByRole("button"))).not.toThrow();
    expect(document.documentElement.getAttribute("data-theme")).toBe("light");
    spy.mockRestore();
  });
});

describe("Progress rail", () => {
  test("four steps, the first is current, each links to its card", () => {
    render(<ProgressRail />);
    const links = screen.getAllByRole("link");
    expect(links.map((l) => l.getAttribute("href"))).toEqual(["#step-1", "#step-2", "#step-3", "#step-4"]);
    expect(links[0].getAttribute("aria-current")).toBe("step");
    expect(links.slice(1).every((l) => l.getAttribute("aria-current") === null)).toBe(true);
    expect(screen.getByRole("navigation", { name: "Progress" })).toBeTruthy();
    expect(links[2].textContent).toContain("Step 3 of 4: How round-ups are invested");
  });
});

describe("Setup cards", () => {
  test("each scenario card shows its shape and a chip; styles change the picture", async () => {
    const { container } = renderWith(<SetupForm />);
    await waitFor(() => expect(container.querySelectorAll(".scenario .spark").length).toBe(4));
    expect([...container.querySelectorAll(".scenario .chip")].map((c) => c.textContent)).toEqual(["Gradual rise", "Dip and back", "Wanders about", "Big swings"]);
    const pts = (i: number) => container.querySelectorAll(".scenario .spark polyline")[i].getAttribute("points");
    const before = pts(0);
    fireEvent.click(screen.getByRole("radio", { name: /Dividend style/ }));
    expect(pts(0)).not.toBe(before);
  });
});

describe("Stylesheet rules", () => {
  test("colours come from tokens: the only literal hex values are the hero button and the brand mark's white", () => {
    const hex = [...css.matchAll(/#[0-9A-Fa-f]{6}\b|#[0-9A-Fa-f]{3}\b/g)].map((m) => m[0].toLowerCase());
    expect(new Set(hex)).toEqual(new Set(["#fff", "#1e1b6e"]));                    // white on the hero, and the hero button's text
  });
  test("reduced motion switches every animation and transition off", () => {
    expect(css).toMatch(/@media \(prefers-reduced-motion: reduce\)[\s\S]*animation: none !important[\s\S]*transition: none !important/);
    expect(css).toMatch(/\.roll::before \{ animation: none !important; \}/);
  });
  test("a visible focus ring is defined for keyboard users", () => {
    expect(css).toMatch(/:focus-visible \{ outline: 3px solid var\(--focus\)/);
  });
  test("no remote font or image is requested by the stylesheet", () => {
    expect(css).not.toMatch(/url\(|@import|https?:\/\//);
  });
});
