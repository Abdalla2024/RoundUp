// Entrance animation: cards fade and rise in as they come into view. Never applied under reduced motion, never hides a focused control.
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { startReveal } from "@/lib/reveal";

type IOCallback = (entries: { target: Element; isIntersecting: boolean }[]) => void;
let ioCallback: IOCallback = () => {};
const observed = new Set<Element>();
class FakeIO { constructor(cb: IOCallback) { ioCallback = cb; } observe(e: Element) { observed.add(e); } unobserve(e: Element) { observed.delete(e); } disconnect() { observed.clear(); } }
function rectAt(el: Element, top: number) { (el as HTMLElement).getBoundingClientRect = () => ({ top, bottom: top + 100, left: 0, right: 100, width: 100, height: 100, x: 0, y: top, toJSON() {} }); }
const raf: FrameRequestCallback[] = [];
beforeEach(() => {
  document.documentElement.setAttribute("data-motion", "on");
  document.body.innerHTML = `<main><div class="card" id="a"></div><div class="card" id="b"></div><div class="card" id="c"></div><div class="chart-box" id="chart" tabindex="0"></div></main>`;
  observed.clear(); raf.length = 0;
  (window as never as { IntersectionObserver: unknown }).IntersectionObserver = FakeIO;
  window.requestAnimationFrame = ((cb: FrameRequestCallback) => { raf.push(cb); return raf.length; }) as never;
  Object.defineProperty(window, "innerHeight", { value: 800, configurable: true });
  const m = (q: string) => ({ matches: false, media: q, addEventListener() {}, removeEventListener() {} });
  window.matchMedia = m as never;
});
afterEach(() => { document.documentElement.removeAttribute("data-motion"); });
const el = (id: string) => document.getElementById(id)!;

describe("startReveal", () => {
  test("elements below the fold wait (pending) and come in when they intersect, one after another", () => {
    rectAt(el("a"), 100); rectAt(el("b"), 1200); rectAt(el("c"), 1400); rectAt(el("chart"), 1600);
    const stop = startReveal();
    expect(el("a").getAttribute("data-reveal")).toBeNull();            // already on screen at load: left alone (no flash)
    expect(el("b").getAttribute("data-reveal")).toBe("pending");
    expect(el("c").getAttribute("data-reveal")).toBe("pending");
    expect(el("chart").getAttribute("data-draw")).toBe("pending");
    ioCallback([{ target: el("b"), isIntersecting: true }, { target: el("c"), isIntersecting: true }, { target: el("chart"), isIntersecting: true }]);
    expect(el("b").getAttribute("data-reveal")).toBe("in");
    expect(el("b").style.getPropertyValue("--rd")).toBe("0ms");
    expect(el("c").style.getPropertyValue("--rd")).toBe("70ms");       // staggered
    expect(el("chart").getAttribute("data-draw")).toBe("in");
    expect(observed.has(el("b"))).toBe(false);                          // once: it never animates out or again
    stop();
  });
  test("under reduced motion nothing is marked, so nothing is hidden or moved", () => {
    document.documentElement.removeAttribute("data-motion");
    rectAt(el("b"), 1200);
    const stop = startReveal();
    expect(el("b").getAttribute("data-reveal")).toBeNull();
    expect(observed.size).toBe(0);
    stop();
  });
  test("an element added later and already on screen is shown with the entrance animation, not left invisible", async () => {
    const stop = startReveal();
    const n = document.createElement("div"); n.className = "card"; n.id = "late"; rectAt(n, 200);
    document.querySelector("main")!.appendChild(n);
    await Promise.resolve();                                            // the MutationObserver callback
    expect(n.getAttribute("data-reveal")).toBe("pending");
    raf.splice(0).forEach((f) => f(0));
    expect(n.getAttribute("data-reveal")).toBe("in");
    stop();
  });
  test("every pending element is shown at once if IntersectionObserver is missing", () => {
    (window as never as { IntersectionObserver: unknown }).IntersectionObserver = undefined;
    rectAt(el("b"), 1200);
    const stop = startReveal();
    expect(el("b").getAttribute("data-reveal")).not.toBe("pending");
    stop();
  });
});
