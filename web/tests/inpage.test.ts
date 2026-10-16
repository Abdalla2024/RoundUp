// In-page links scroll smoothly (instantly under reduced motion), move keyboard focus to the target's heading, and tell the progress rail.
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { goTo, INPAGE_EVENT, installInPageLinks, prefersReducedMotion } from "@/lib/inpage";

function reduced(on: boolean) {
  window.matchMedia = ((q: string) => ({ matches: on && q.includes("reduce"), media: q, addEventListener() {}, removeEventListener() {} })) as never;
}
const scroll = vi.fn();
beforeEach(() => {
  document.body.innerHTML = `<a id="skip" href="#main">Skip</a><a id="go" href="#step-2">Step 2</a><a id="nowhere" href="#missing">x</a>
    <main id="main"><fieldset id="step-2" data-step="2"><legend><span class="step-title">Market scenario</span></legend></fieldset>
    <section id="results"><h2>Value over time</h2></section></main>`;
  document.querySelectorAll("fieldset, section").forEach((e) => { (e as HTMLElement).getBoundingClientRect = () => ({ top: 600 } as DOMRect); });
  Element.prototype.scrollIntoView = scroll; scroll.mockReset(); history.replaceState(null, "", "/");
  vi.useFakeTimers();
});
afterEach(() => { vi.useRealTimers(); });

describe("goTo", () => {
  test("scrolls smoothly, then (when the scroll has ended) focuses the step's heading without scrolling again", () => {
    reduced(false);
    const heard: string[] = []; window.addEventListener(INPAGE_EVENT, (e) => heard.push((e as CustomEvent).detail.id), { once: true });
    expect(goTo("step-2")).toBe(true);
    expect(scroll).toHaveBeenCalledWith({ behavior: "smooth", block: "start" });
    expect(location.hash).toBe("#step-2");
    expect(heard).toEqual(["step-2"]);
    expect(document.activeElement).not.toBe(document.querySelector(".step-title"));     // not before the scroll has ended
    document.dispatchEvent(new Event("scrollend"));
    const title = document.querySelector<HTMLElement>(".step-title")!;
    expect(document.activeElement).toBe(title);
    expect(title.getAttribute("tabindex")).toBe("-1");                                 // focusable by script, not an extra Tab stop
  });
  test("falls back to a timer when the browser never sends scrollend", () => {
    reduced(false);
    goTo("results");
    vi.advanceTimersByTime(1500);
    expect(document.activeElement).toBe(document.querySelector("#results h2"));
  });
  test("under reduced motion the jump is instant and focus moves at once", () => {
    reduced(true);
    expect(prefersReducedMotion()).toBe(true);
    goTo("step-2");
    expect(scroll).toHaveBeenCalledWith({ behavior: "auto", block: "start" });
    expect(document.activeElement).toBe(document.querySelector(".step-title"));
  });
  test("a section already in place gets focus at once (no scroll, so no scrollend to wait for)", () => {
    reduced(false);
    (document.getElementById("step-2") as HTMLElement).getBoundingClientRect = () => ({ top: 0 } as DOMRect);
    goTo("step-2");
    expect(document.activeElement).toBe(document.querySelector(".step-title"));
  });
  test("an unknown id does nothing (the browser keeps its default)", () => {
    reduced(false);
    expect(goTo("missing")).toBe(false);
    expect(scroll).not.toHaveBeenCalled();
  });
});

describe("focus is never moved against the person's wishes", () => {
  test("a newer click cancels the older one's pending focus move", () => {
    reduced(false);
    goTo("step-2"); goTo("results");
    document.dispatchEvent(new Event("scrollend"));
    expect(document.activeElement).toBe(document.querySelector("#results h2"));      // the latest only
    vi.advanceTimersByTime(2000);
    expect(document.activeElement).toBe(document.querySelector("#results h2"));      // and the older timer did nothing
  });
  test("if the person starts typing or tabbing before the scroll ends, focus stays where they put it", () => {
    reduced(false);
    goTo("step-2");
    window.dispatchEvent(new Event("keydown"));
    document.dispatchEvent(new Event("scrollend")); vi.advanceTimersByTime(2000);
    expect(document.activeElement).not.toBe(document.querySelector(".step-title"));
  });
  test("if focus is already on some other control when the scroll ends, it is left there", () => {
    reduced(false);
    document.getElementById("nowhere")!.focus();
    document.getElementById("go")!.focus();
    goTo("step-2");
    document.getElementById("nowhere")!.focus();
    document.dispatchEvent(new Event("scrollend"));
    expect(document.activeElement).toBe(document.getElementById("nowhere"));
  });
});

describe("installInPageLinks (one click listener for every in-page link)", () => {
  test("a plain click on an in-page link is handled; the skip link, modified clicks and missing targets are left to the browser", () => {
    reduced(false);
    const off = installInPageLinks();
    const click = (sel: string, init: MouseEventInit = {}) => {
      const ev = new MouseEvent("click", { bubbles: true, cancelable: true, button: 0, ...init });
      document.querySelector(sel)!.dispatchEvent(ev); return ev.defaultPrevented;
    };
    expect(click("#go")).toBe(true);
    expect(scroll).toHaveBeenCalledTimes(1);
    expect(click("#skip")).toBe(false);                    // "Skip to main content" keeps its native jump
    expect(click("#go", { ctrlKey: true })).toBe(false);   // open-in-new-tab and friends
    expect(click("#nowhere")).toBe(false);
    expect(scroll).toHaveBeenCalledTimes(1);
    off();
    expect(click("#go")).toBe(false);
  });
});
