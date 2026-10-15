import type { Page } from "@playwright/test";

export interface Issue { kind: string; detail: string }

/**
 * Layout checks that run in the browser on whatever is on screen. They measure real boxes, so they catch what
 * axe, text assertions and screenshots-by-eye do not (stage 6: overlapping CSV controls shipped because no test
 * looked at where things were drawn, only at whether they existed and were labelled):
 *  - overlap:  two visible controls or text blocks whose boxes intersect (neither contains the other)
 *  - clipped:  text cut off by its own box or by an ancestor that hides overflow; a <select> whose chosen option
 *              is wider than the box; text that spills out of its block
 *  - edge:     anything drawn outside the left or right edge of the window, or the page scrolling sideways
 * Intentionally scrollable regions (.table-scroll) are skipped.
 */
const SELECT_SAFETY_PX = 12;

export async function geometryIssues(page: Page, opts: { selectValues?: boolean } = {}): Promise<Issue[]> {
  const selectValues = opts.selectValues !== false;
  return page.evaluate(([selectValues, SELECT_SAFETY_PX]) => {
    const issues: { kind: string; detail: string }[] = [];
    const vw = document.documentElement.clientWidth;
    const name = (e: Element) => {
      const t = (e.textContent ?? "").replace(/\s+/g, " ").trim().slice(0, 40);
      return `${e.tagName.toLowerCase()}${e.id ? "#" + e.id : ""}${e.className && typeof e.className === "string" ? "." + e.className.split(" ")[0] : ""}${t ? ` “${t}”` : ""}`;
    };
    const hiddenByStyle = (e: Element) => {
      for (let n: Element | null = e; n && n !== document.body; n = n.parentElement) {
        const cs = getComputedStyle(n);
        if (cs.display === "none" || cs.visibility === "hidden" || Number(cs.opacity) === 0) return true;
        if (n.tagName === "DETAILS" && !(n as HTMLDetailsElement).open) {       // closed <details>: only the summary is drawn
          const sum = n.querySelector(":scope > summary");
          if (!(sum && sum.contains(e))) return true;
        }
        if (n.classList.contains("visually-hidden") || n.classList.contains("skip") || n.closest("[hidden]")) return true;
        if (cs.clip === "rect(0px, 0px, 0px, 0px)" || (cs.position === "absolute" && n.clientWidth <= 1 && n.clientHeight <= 1)) return true;
      }
      return false;
    };
    const inScroller = (e: Element) => Boolean(e.closest(".table-scroll, .recharts-wrapper, svg"));
    const all = [...document.body.querySelectorAll("*")].filter((e) => {
      const r = e.getBoundingClientRect();
      return r.width > 0 && r.height > 0 && !hiddenByStyle(e);
    });
    const controls = all.filter((e) => e.matches("a[href], button, input:not([type=hidden]), select, textarea, summary, [tabindex]:not([tabindex='-1'])"));
    const hasOwnText = (e: Element) => [...e.childNodes].some((n) => n.nodeType === 3 && (n.textContent ?? "").trim() !== "");
    const texts = all.filter((e) => hasOwnText(e) && !e.matches("script, style, option, title, desc"));
    // Sticky and fixed elements (the progress rail) are meant to sit on top of the page as it scrolls, so they are not "overlapping" what
    // passes under them; they still count for the window-edge check below.
    const overlays = (e: Element) => { for (let n: Element | null = e; n && n !== document.body; n = n.parentElement) { const p = getComputedStyle(n).position; if (p === "sticky" || p === "fixed") return true; } return false; };
    const boxed = [...new Set([...controls, ...texts])].filter((e) => !inScroller(e) && !e.closest("dialog:not([open])") && !e.closest(".decor"));

    // 1. overlap
    const rects = new Map(boxed.map((e) => [e, e.getBoundingClientRect()] as const));
    // Inline text that wraps has one bounding box around all its lines, which can cover a neighbour that is not
    // really touched; compare the individual line boxes instead.
    const lines = new Map(boxed.map((e) => [e, [...e.getClientRects()].filter((r) => r.width > 0 && r.height > 0)] as const));
    for (let i = 0; i < boxed.length; i++) {
      for (let j = i + 1; j < boxed.length; j++) {
        const a = boxed[i], b = boxed[j];
        if (a.contains(b) || b.contains(a)) continue;
        if (overlays(a) !== overlays(b)) continue;                 // a sticky element over the scrolled page is by design
        const ra = rects.get(a)!, rb = rects.get(b)!;
        if (Math.min(ra.right, rb.right) - Math.max(ra.left, rb.left) <= 2 || Math.min(ra.bottom, rb.bottom) - Math.max(ra.top, rb.top) <= 2) continue;
        for (const la of lines.get(a)!) {
          for (const lb of lines.get(b)!) {
            const w = Math.min(la.right, lb.right) - Math.max(la.left, lb.left);
            const h = Math.min(la.bottom, lb.bottom) - Math.max(la.top, lb.top);
            if (w > 2 && h > 2) {
              // a label belongs to its own radio/checkbox card: the input sits inside the card by design
              if (a.closest("label") && a.closest("label") === b.closest("label")) continue;
              issues.push({ kind: "overlap", detail: `${name(a)}  ×  ${name(b)}  (${Math.round(w)}×${Math.round(h)} px)` });
            }
          }
        }
      }
    }

    // 2. clipped text
    for (const e of texts) {
      if (inScroller(e)) continue;
      const cs = getComputedStyle(e);
      const clips = (s: CSSStyleDeclaration) => ["hidden", "clip", "auto", "scroll"].includes(s.overflowX);
      if (clips(cs) && e.scrollWidth > e.clientWidth + 1) issues.push({ kind: "clipped", detail: `${name(e)} is wider than its box (${e.scrollWidth} > ${e.clientWidth})` });
      if (cs.textOverflow === "ellipsis" && e.scrollWidth > e.clientWidth + 1) issues.push({ kind: "clipped", detail: `${name(e)} is cut with an ellipsis` });
      if (!e.matches("select, input, textarea, button, a, summary") && cs.display !== "inline" && e.clientWidth > 0 && e.scrollWidth > e.clientWidth + 1 && !clips(cs)) {
        issues.push({ kind: "clipped", detail: `${name(e)} spills out of its own box (${e.scrollWidth} > ${e.clientWidth})` });
      }
      const r = e.getBoundingClientRect();
      for (let p = e.parentElement; p && p !== document.body; p = p.parentElement) {
        const ps = getComputedStyle(p);
        if (p.classList.contains("table-scroll") || p.tagName === "DIALOG") break;
        if (["hidden", "clip"].includes(ps.overflowX) || ["hidden", "clip"].includes(ps.overflowY)) {
          const pr = p.getBoundingClientRect();
          if (r.right > pr.right + 1 || r.bottom > pr.bottom + 1 || r.left < pr.left - 1 || r.top < pr.top - 1) {
            issues.push({ kind: "clipped", detail: `${name(e)} is cut off by ${name(p)}` });
          }
        }
      }
    }
    const measure = document.createElement("canvas").getContext("2d")!;
    for (const s of selectValues ? document.querySelectorAll("select") : []) {
      if (hiddenByStyle(s)) continue;
      const cs = getComputedStyle(s), sel = (s as HTMLSelectElement).selectedOptions[0];
      if (!sel) continue;
      measure.font = `${cs.fontWeight} ${cs.fontSize} ${cs.fontFamily}`;
      const room = s.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight) - 24;     // 24 px: the arrow
      const need = measure.measureText(sel.textContent ?? "").width;
      // SAFETY: the same text measured 279 px on macOS and 284 px under Linux (GitHub CI), so a select that fits with no
      // spare room on one platform clips on the other. Require 12 px (about 4%) to spare.
      if (need + SELECT_SAFETY_PX > room + 1) issues.push({ kind: "clipped", detail: `select ${name(s.closest(".field") ?? s)}: “${(sel.textContent ?? "").trim().slice(0, 40)}” needs ${Math.round(need)} px (+${SELECT_SAFETY_PX} px safety for other platforms' fonts), has ${Math.round(room)}` });
    }

    // 3. window edges
    for (const e of boxed) {
      const r = rects.get(e)!;
      if (r.left < -1 || r.right > vw + 1) issues.push({ kind: "edge", detail: `${name(e)} is drawn outside the window (${Math.round(r.left)}…${Math.round(r.right)} of ${vw})` });
    }
    if (document.documentElement.scrollWidth > vw + 1) issues.push({ kind: "edge", detail: `the page scrolls sideways (${document.documentElement.scrollWidth} > ${vw})` });
    return issues;
  }, [selectValues, SELECT_SAFETY_PX] as const);
}
