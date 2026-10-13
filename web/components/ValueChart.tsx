"use client";
// The ONLY file allowed to turn engine strings into numbers, and only for drawing positions (axis scale, line
// coordinates). Every figure a person reads is the original API string (tests/no-money-arithmetic.test.ts).
import dynamic from "next/dynamic";
import { useState } from "react";
import { COPY } from "@/lib/copy";
import { longDate, money } from "@/lib/format";
import type { Point, Result } from "@/lib/types";

// Recharts is loaded only when a chart is shown; a same-size placeholder avoids layout shift.
const ChartCanvas = dynamic(() => import("./ChartCanvas"), { ssr: false,
  loading: () => <div className="chart-loading muted small" role="status">Loading chart…</div> });

export function niceTop(v: number): number {               // drawing only: axis top at 1/1.5/2/2.5/3/4/5 x 10^n
  const p = Math.pow(10, Math.floor(Math.log10(v || 1)));
  return ([1, 1.5, 2, 2.5, 3, 4, 5, 10].find((m) => m * p >= v) ?? 10) * p;
}
export function chartTop(points: Point[]): number {
  return points.length ? niceTop(Math.max(...points.map((p) => Math.max(Number(p.value), Number(p.added))))) : 1;
}

export function chartSummary(result: Result): string {
  const pts = result.series, f = pts[0], l = pts[pts.length - 1];
  if (!f) return COPY.noTradingDay;
  if (pts.length === 1) return `On ${longDate(f.date)} the value is ${money(f.value)} and the round-ups added are ${money(f.added)}.`;
  if (pts.every((p) => p.value === f.value)) {             // string comparison only: "unchanged", not computed
    return `From ${longDate(f.date)} to ${longDate(l.date)} the value stays at ${money(f.value)}, while the round-ups added go from ${money(f.added)} to ${money(l.added)}.`;
  }
  return `From ${longDate(f.date)} to ${longDate(l.date)} the value goes from ${money(f.value)} to ${money(l.value)}, with ups and downs in between, while the round-ups added go from ${money(f.added)} to ${money(l.added)}.`;
}

export function pointText(p: Point, label = "value"): string {
  return `${longDate(p.date)}: ${label} ${money(p.value)}, round-ups added ${money(p.added)}.` +
    (p.carried === "true" ? " Price carried from the last trading day." : "");
}

export function ValueChart({ result, title, color = "var(--series-1)", yTop, small, label = "Value", level = 2 }:
  { result: Result; title: string; color?: string; yTop?: number; small?: boolean; label?: string; level?: 2 | 3 }) {
  const pts = result.series;
  const top = yTop ?? chartTop(pts);
  const [showTable, setShowTable] = useState(false);
  const [active, setActive] = useState<number | null>(null);
  const id = title.replace(/\W+/g, "-").toLowerCase();
  const heading = level === 2 ? <h2 id={`${id}-t`} style={{ fontSize: 20 }}>{title}</h2>
                              : <h3 id={`${id}-t`} style={{ fontSize: small ? 16 : 20 }}>{title}</h3>;
  if (pts.length === 0) {
    return (<figure aria-labelledby={`${id}-t`}>{heading}<p className="muted">{COPY.noTradingDay}</p></figure>);
  }
  // Keyboard reading (reviewer M6): our own handler instead of Recharts' accessibility layer, so Home/End/PageUp/
  // PageDown work, nothing shows until asked, and the current point is announced through a polite live region.
  const page = result.series_resolution === "weekly" ? 52 : 21;     // about a year of weeks, or a month of days
  function onKey(e: React.KeyboardEvent) {
    const last = pts.length - 1, cur = active;
    const next = { ArrowRight: cur === null ? 0 : cur + 1, ArrowLeft: cur === null ? last : cur - 1, Home: 0, End: last,
                   PageDown: (cur ?? -1) + page, PageUp: (cur ?? last + 1) - page }[e.key];
    if (next === undefined) return;
    e.preventDefault();
    setActive(Math.min(last, Math.max(0, next)));
  }
  return (
    <figure aria-labelledby={`${id}-t`}>
      {heading}
      <ul className="legend" aria-hidden="true">
        <li><span className="swatch" style={{ borderColor: color }} />{label}</li>
        <li><span className="swatch dashed" style={{ borderColor: "var(--added)" }} />Round-ups added so far</li>
      </ul>
      <div className={`chart-box${small ? " small" : ""}`} tabIndex={0} role="group" aria-label={`${title}. ${COPY.chartKeys}`}
        aria-describedby={`${id}-sum`} onKeyDown={onKey} data-testid="chart">
        <ChartCanvas pts={pts} title={title} summary={chartSummary(result)} top={top} color={color} label={label}
          active={active} onPick={setActive} />
      </div>
      <p className="small chart-readout" aria-live="polite" data-testid="chart-readout">
        {active !== null ? pointText(pts[active], label === "Value" ? "value" : `${label} value`) : ""}</p>
      <figcaption>{result.series_rule} {COPY.datesNote}</figcaption>
      <p className="small muted" id={`${id}-sum`}>{chartSummary(result)}</p>
      <p className="small muted">{COPY.chartKeys}</p>
      <button type="button" className="linklike" aria-expanded={showTable} onClick={() => setShowTable(!showTable)}
        style={{ color: "var(--link)", fontWeight: 600 }}>
        {showTable ? "Hide the table" : "Show the chart as a table"}</button>
      {showTable && (
        <div className="table-scroll" tabIndex={0} role="region" aria-label={`${title} as a table`}>
          <table><caption className="visually-hidden">{title}: value and round-ups added at each chart point</caption>
            <thead><tr><th scope="col">Date</th><th scope="col">Round-ups added</th><th scope="col">{label}</th></tr></thead>
            <tbody>{pts.map((p) => <tr key={p.date}><td>{longDate(p.date)}</td><td>{money(p.added)}</td><td>{money(p.value)}</td></tr>)}</tbody>
          </table></div>)}
    </figure>
  );
}
