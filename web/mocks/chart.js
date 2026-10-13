// RoundUp mock chart: value line vs "round-ups added" line, as inline SVG.
// Numbers are API strings. Number() is used ONLY for drawing positions, never to compute figures shown to people.
(function () {
  const NS = "http://www.w3.org/2000/svg";
  const money = (s) => {
    const neg = s.startsWith("-");
    const [w, f] = (neg ? s.slice(1) : s).split(".");
    return (neg ? "−$" : "$") + w.replace(/\B(?=(\d{3})+(?!\d))/g, ",") + "." + f;
  };
  const longDate = (iso) => new Date(iso + "T00:00:00Z").toLocaleDateString("en-US",
    { year: "numeric", month: "short", day: "numeric", timeZone: "UTC" });
  window.fmt = { money, longDate };

  // live-region updates are throttled so holding an arrow key does not flood a screen reader
  const timers = new WeakMap();
  function announce(node, text) {
    clearTimeout(timers.get(node));
    timers.set(node, setTimeout(() => { node.textContent = text; }, 250));
  }

  function el(name, attrs, parent) {
    const n = document.createElementNS(NS, name);
    for (const [k, v] of Object.entries(attrs || {})) n.setAttribute(k, v);
    if (parent) parent.appendChild(n);
    return n;
  }

  const STEPS = { 1: 5, 1.5: 3, 2: 4, 2.5: 5, 3: 3, 4: 4, 5: 5 };   // axis top -> number of round ticks
  function niceMax(v) {                       // round the axis top up to 1, 1.5, 2, 2.5, 3, 4 or 5 x 10^n
    const p = Math.pow(10, Math.floor(Math.log10(v || 1)));
    for (const m of [1, 1.5, 2, 2.5, 3, 4, 5, 10]) if (m * p >= v) return m * p;
    return 10 * p;
  }
  window.niceMax = niceMax;

  // opts: {points, title, cls, yMax, height, tooltipEl, summaryLabel}
  window.drawChart = function (container, opts) {
    const W = Math.max(300, Math.round(container.clientWidth || 720));   // real pixel width: text stays legible
    const H = opts.height || (W < 500 ? 240 : 300), L = 56, R = W < 500 ? 60 : 92, T = 16, B = 32;
    const pts = opts.points;
    const yMax = opts.yMax || niceMax(Math.max(...pts.map((p) => Math.max(+p.value, +p.added))));
    const x = (i) => L + (i / (pts.length - 1)) * (W - L - R);
    const y = (v) => T + (1 - v / yMax) * (H - T - B);
    const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, class: "chart", role: "img", tabindex: "0",
                            "aria-label": opts.summaryLabel });
    const lead = yMax / Math.pow(10, Math.floor(Math.log10(yMax)));
    const steps = STEPS[lead] || 5;
    for (let k = 0; k <= steps; k++) {           // recessive horizontal grid, y from $0
      const v = (yMax * k) / steps;
      el("line", { x1: L, x2: W - R, y1: y(v), y2: y(v), class: k ? "grid" : "axis" }, svg);
      el("text", { x: L - 8, y: y(v) + 4, "text-anchor": "end" }, svg).textContent =
        "$" + v.toLocaleString("en-US", { maximumFractionDigits: 0 });
    }
    let lastYear = null;                         // x axis: one tick per year (or per quarter for short ranges)
    const short = pts.length < 400;
    const everyOther = W < 500 && !short;        // fewer year labels on narrow screens
    pts.forEach((p, i) => {
      const yr = p.date.slice(0, 4), q = short ? p.date.slice(0, 7) : yr;
      if (q !== lastYear && (!short || ["01", "04", "07", "10"].includes(p.date.slice(5, 7)))) {
        if ((lastYear !== null || i === 0) && !(everyOther && i > 0 && +yr % 2 !== +pts[0].date.slice(0, 4) % 2)) {
          el("text", { x: x(i), y: H - 10, "text-anchor": "middle" }, svg).textContent =
            short ? new Date(p.date + "T00:00:00Z").toLocaleDateString("en-US", { month: "short", timeZone: "UTC" }) : yr;
        }
        lastYear = q;
      }
    });
    const path = (key) => pts.map((p, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(+p[key]).toFixed(1)}`).join("");
    el("path", { d: path("added"), class: "added" }, svg);
    el("path", { d: path("value"), class: "value" + (opts.cls ? " " + opts.cls : "") }, svg);
    const last = pts[pts.length - 1];
    const ly = { v: y(+last.value), a: y(+last.added) };
    if (Math.abs(ly.v - ly.a) < 16) { if (ly.v < ly.a) ly.a = ly.v + 16; else ly.v = ly.a + 16; }
    el("text", { x: W - R + 8, y: ly.v + 4, class: "label" }, svg).textContent = opts.valueLabel || "Value";
    el("text", { x: W - R + 8, y: ly.a + 4, class: "label" }, svg).textContent = "Added";

    const cursor = el("line", { y1: T, y2: H - B, class: "cursor", visibility: "hidden" }, svg);
    const dotV = el("circle", { r: 4, class: "dot", fill: "var(--series-" + (opts.cls === "b" ? 2 : 1) + ")",
                                visibility: "hidden" }, svg);
    const dotA = el("circle", { r: 4, class: "dot", fill: "var(--added)", visibility: "hidden" }, svg);
    let idx = pts.length - 1;
    function show(i) {
      idx = Math.max(0, Math.min(pts.length - 1, i));
      const p = pts[idx];
      for (const n of [cursor, dotV, dotA]) n.setAttribute("visibility", "visible");
      cursor.setAttribute("x1", x(idx)); cursor.setAttribute("x2", x(idx));
      dotV.setAttribute("cx", x(idx)); dotV.setAttribute("cy", y(+p.value));
      dotA.setAttribute("cx", x(idx)); dotA.setAttribute("cy", y(+p.added));
      if (opts.tooltipEl) announce(opts.tooltipEl,
        `${longDate(p.date)}: value ${money(p.value)}, round-ups added ${money(p.added)}` +
        (p.carried === "true" ? " (price carried from the last trading day)" : ""));
    }
    svg.addEventListener("pointermove", (e) => {
      const r = svg.getBoundingClientRect();
      const px = ((e.clientX - r.left) / r.width) * W;
      show(Math.round(((px - L) / (W - L - R)) * (pts.length - 1)));
    });
    svg.addEventListener("keydown", (e) => {     // keyboard: arrows move a week (or day), Home/End jump
      const step = { ArrowRight: 1, ArrowLeft: -1, PageUp: 13, PageDown: -13 }[e.key];
      if (step) { show(idx + step); e.preventDefault(); }
      if (e.key === "Home") { show(0); e.preventDefault(); }
      if (e.key === "End") { show(pts.length - 1); e.preventDefault(); }
    });
    svg.addEventListener("focus", () => show(idx));
    container.appendChild(svg);
    return { yMax };
  };
})();
