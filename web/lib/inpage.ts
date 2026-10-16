// In-page links (the progress rail, "Start a simulation", any "#section" link). Behaviour on a plain click:
//  - scroll smoothly to the section (instantly under prefers-reduced-motion; MDN: honour the "reduce" request by removing the motion);
//    the sticky header is allowed for by `scroll-margin-top` in the stylesheet;
//  - put the address bar on the section (so Back and sharing work);
//  - tell the progress rail which step was chosen (INPAGE_EVENT);
//  - once the scroll has ended (scrollend, with a timer fallback), move keyboard focus to the section's heading WITHOUT scrolling again
//    (focus({ preventScroll: true })). The heading gets tabindex="-1": focusable by script, not an extra Tab stop.
// Focus only moves because the person activated the link; nothing else in the app moves focus on its own.
// The skip link ("#main"), modified clicks (new tab, etc.) and links to ids that do not exist keep the browser's own behaviour.
export const INPAGE_EVENT = "roundup:inpage";
const FALLBACK_MS = 1200;

export function prefersReducedMotion(): boolean {
  return typeof window !== "undefined" && typeof window.matchMedia === "function" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/** The element that should receive focus for a section: a step's title, a heading, or the section's first heading. */
export function focusTargetFor(target: HTMLElement): HTMLElement {
  if (target.matches("fieldset")) return target.querySelector<HTMLElement>(".step-title") ?? target;
  if (target.matches("h1, h2, h3, h4")) return target;
  return target.querySelector<HTMLElement>("h1, h2, h3") ?? target;
}

let cancelPending: (() => void) | null = null;

export function goTo(id: string): boolean {
  const target = document.getElementById(id);
  if (!target) return false;
  cancelPending?.();                                   // a newer choice replaces an older one: only the latest may move focus
  const reduced = prefersReducedMotion();
  const clicked = document.activeElement;
  const gap = target.getBoundingClientRect().top - (Number.parseInt(getComputedStyle(target).scrollMarginTop, 10) || 0);
  const noScrollNeeded = gap < 2 && gap > -2;           // already in place: scrollend would never come
  target.scrollIntoView({ behavior: reduced ? "auto" : "smooth", block: "start" });
  if (location.hash !== `#${id}`) history.pushState(history.state, "", `#${id}`);
  window.dispatchEvent(new CustomEvent(INPAGE_EVENT, { detail: { id, reduced } }));
  const focusIt = () => {
    // Only if the person has not moved on: focus is still on the link they used (or on nothing in particular).
    const now = document.activeElement;
    if (now && now !== document.body && now !== clicked) return;
    const el = focusTargetFor(target);
    if (!el.hasAttribute("tabindex")) el.setAttribute("tabindex", "-1");
    el.focus({ preventScroll: true });
  };
  if (reduced || noScrollNeeded) { focusIt(); return true; }
  const finish = () => { cancel(); focusIt(); };
  const timer = setTimeout(finish, FALLBACK_MS);
  // Typing, wheel, touch or tabbing elsewhere means the person has taken over: do not move focus afterwards.
  const abort = () => cancel();
  const cancel = () => {
    clearTimeout(timer);
    document.removeEventListener("scrollend", finish);
    for (const ev of ["keydown", "wheel", "touchstart"]) window.removeEventListener(ev, abort);
    if (cancelPending === cancel) cancelPending = null;
  };
  cancelPending = cancel;
  document.addEventListener("scrollend", finish);
  for (const ev of ["keydown", "wheel", "touchstart"]) window.addEventListener(ev, abort, { passive: true });
  return true;
}

/** One click listener for every in-page link. Returns a function that removes it. */
export function installInPageLinks(): () => void {
  const onClick = (e: MouseEvent) => {
    if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    const a = (e.target as Element | null)?.closest?.("a[href^='#']");
    if (!a) return;
    const id = decodeURIComponent(a.getAttribute("href")!.slice(1));
    if (!id || id === "main" || !document.getElementById(id)) return;
    e.preventDefault();
    goTo(id);
  };
  document.addEventListener("click", onClick);
  return () => document.removeEventListener("click", onClick);
}
