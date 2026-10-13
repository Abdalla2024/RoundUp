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
  return niceTop(Math.max(...points.map((p) => Math.max(Number(p.value), Number(p.added)))));
}

export function chartSummary(result: Result): string {
  const pts = result.series, f = pts[0], l = pts[pts.length - 1];
  return `From ${longDate(f.date)} to ${longDate(l.date)} the value goes from ${money(f.value)} to ${money(l.value)}, with ups and downs in between, while the round-ups added go from ${money(f.added)} to ${money(l.added)}.`;
}

export function ValueChart({ result, title, color = "var(--series-1)", yTop, small, label = "Value", level = 2 }:
  { result: Result; title: string; color?: string; yTop?: number; small?: boolean; label?: string; level?: 2 | 3 }) {
  const pts = result.series;
  const top = yTop ?? chartTop(pts);
  const [showTable, setShowTable] = useState(false);
  const id = title.replace(/\W+/g, "-").toLowerCase();
  return (
    <figure aria-labelledby={`${id}-t`}>
      {level === 2 ? <h2 id={`${id}-t`} style={{ fontSize: 20 }}>{title}</h2>
                   : <h3 id={`${id}-t`} style={{ fontSize: small ? 16 : 20 }}>{title}</h3>}
      <ul className="legend" aria-hidden="true">
        <li><span className="swatch" style={{ borderColor: color }} />{label}</li>
        <li><span className="swatch dashed" style={{ borderColor: "var(--added)" }} />Round-ups added so far</li>
      </ul>
      <div className={`chart-box${small ? " small" : ""}`} aria-describedby={`${id}-sum`}>
        <ChartCanvas pts={pts} title={title} summary={chartSummary(result)} top={top} color={color} label={label} />
      </div>
      <figcaption>{result.series_rule} {COPY.datesNote}</figcaption>
      <p className="small muted" id={`${id}-sum`}>{chartSummary(result)}</p>
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
