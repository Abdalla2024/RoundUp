// Entrance animation, CSS first. Elements that match REVEAL_SELECTOR and start below the fold are marked data-reveal="pending"
// (faded out and a little low, only while <html data-motion="on">, which is set before the first paint unless the person prefers reduced
// motion); when they scroll into view they become data-reveal="in", with a short stagger, and transition to normal. Once. Charts do the
// same with data-draw (a left-to-right reveal). Elements already on screen when the page loads are left alone (no flash), and
// elements added later (the results page renders after the simulation returns) that are on screen get the entrance at once.
// Nothing is removed from the page or from the accessibility tree: only opacity and transform change, and a focused element is never
// hidden (the stylesheet shows any pending element that contains focus).
export const REVEAL_SELECTOR = ".step-card, .stat, .results-hero, .strip, .card, .diff-summary, .saved-card, .compare-grid > *, .multiples > *";
export const DRAW_SELECTOR = ".chart-box";
const STAGGER_MS = 70, MAX_STEPS = 5;

const motionOn = () => document.documentElement.getAttribute("data-motion") === "on";
const onScreen = (e: Element) => { const r = e.getBoundingClientRect(); return r.top < window.innerHeight && r.bottom > 0; };

export function startReveal(): () => void {
  if (!motionOn()) return () => {};
  const attr = (e: Element) => (e.matches(DRAW_SELECTOR) ? "data-draw" : "data-reveal");
  let io: IntersectionObserver | null = null;
  const show = (batch: Element[]) => batch.forEach((e, i) => {
    (e as HTMLElement).style.setProperty("--rd", `${(i < MAX_STEPS ? i : MAX_STEPS) * STAGGER_MS}ms`);
    e.setAttribute(attr(e), "in");
    io?.unobserve(e);
  });
  if (typeof IntersectionObserver === "function") {
    io = new IntersectionObserver((entries) => show(entries.filter((x) => x.isIntersecting).map((x) => x.target)), { rootMargin: "0px 0px -8% 0px" });
  }
  const seen = new WeakSet<Element>();
  const scan = (root: ParentNode, initial: boolean) => {
    const fresh: Element[] = [];
    root.querySelectorAll(`${REVEAL_SELECTOR}, ${DRAW_SELECTOR}`).forEach((e) => {
      if (seen.has(e) || e.closest("dialog")) return;
      if (e.matches(REVEAL_SELECTOR) && e.parentElement?.closest(REVEAL_SELECTOR)) return;    // a card inside a card moves with its parent
      seen.add(e);
      if (initial && onScreen(e)) return;                       // on screen at load: no flash, no animation
      if (!io) return;                                          // no IntersectionObserver: leave it visible
      e.setAttribute(attr(e), "pending");
      if (onScreen(e)) fresh.push(e); else io.observe(e);
    });
    if (fresh.length) requestAnimationFrame(() => show(fresh));
  };
  // Safety: at the very bottom of the page nothing can intersect the shrunk viewport any more, so show whatever is still waiting.
  const atBottom = () => window.scrollY + window.innerHeight >= document.documentElement.scrollHeight - 2;
  const onScroll = () => { if (atBottom()) show([...document.querySelectorAll('[data-reveal="pending"], [data-draw="pending"]')]); };
  window.addEventListener("scroll", onScroll, { passive: true });
  scan(document, true);
  const mo = new MutationObserver((muts) => {
    for (const m of muts) m.addedNodes.forEach((n) => { if (n instanceof Element) { scan(n.parentElement ?? document, false); } });
  });
  mo.observe(document.querySelector("main") ?? document.body, { childList: true, subtree: true });
  return () => { mo.disconnect(); io?.disconnect(); window.removeEventListener("scroll", onScroll); };
}
