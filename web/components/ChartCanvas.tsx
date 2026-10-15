"use client";
// Drawing only (lazy-loaded): converts engine strings to numbers for line coordinates and axis positions.
// Every figure a person reads in the tooltip is the original API string.
import { useId, useMemo } from "react";
import { Area, CartesianGrid, ComposedChart, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { longDate, money } from "@/lib/format";
import type { Point } from "@/lib/types";

export default function ChartCanvas({ pts, title, summary, top, color, label, active, onPick }:
  { pts: Point[]; title: string; summary: string; top: number; color: string; label: string;
    active: number | null; onPick: (i: number) => void }) {
  const gid = `fill-${useId().replace(/[^a-zA-Z0-9]/g, "")}`;
  const data = useMemo(() => pts.map((p, i) => ({ i, date: p.date, v: Number(p.value), a: Number(p.added) })), [pts]);
  // one x-axis tick per year (first chart point of each year), or per quarter for short ranges
  const short = pts.length < 400;
  const ticks = useMemo(() => {
    const key = (d: string) => (short ? `${d.slice(0, 4)}-${Math.floor((Number.parseInt(d.slice(5, 7), 10) - 1) / 3)}` : d.slice(0, 4));
    return pts.filter((p, i) => i === 0 || key(p.date) !== key(pts[i - 1].date)).map((p) => p.date);
  }, [pts, short]);
  // "Jan 2020", never "Jan 20" (which reads as a day of the month)
  const tickLabel = (d: string) => (short
    ? new Date(`${d}T00:00:00Z`).toLocaleDateString("en-US", { month: "short", year: "numeric", timeZone: "UTC" }) : d.slice(0, 4));
  // axis positions only (not API figures): cents shown when the scale is under $10, so "$0.40", not "$0.4"
  const cents = top < 10;
  const yLabel = (n: number) => `$${n.toLocaleString("en-US", { minimumFractionDigits: cents ? 2 : 0, maximumFractionDigits: 2 })}`;
  return (
    <ResponsiveContainer width="100%" height="100%">
      <ComposedChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 8 }} title={title} desc={summary} accessibilityLayer={false}
        onClick={(s) => { const i = Number(s?.activeTooltipIndex); if (Number.isInteger(i) && i >= 0) onPick(i); }}>
        <defs>
          <linearGradient id={gid} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.34} /><stop offset="100%" stopColor={color} stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <CartesianGrid vertical={false} stroke="var(--line)" />
        <XAxis dataKey="date" ticks={ticks} tickFormatter={tickLabel} minTickGap={16} interval="preserveStartEnd"
          stroke="var(--control)" tick={{ fill: "var(--ink2)", fontSize: 12 }} />
        <YAxis domain={[0, top]} tickFormatter={yLabel} stroke="var(--control)" tick={{ fill: "var(--ink2)", fontSize: 12 }} width={64} />
        <Tooltip content={({ active: hover, payload }) => {
          if (!hover || !payload?.length) return null;
          const p = pts[(payload[0].payload as { i: number }).i];
          return (<div className="card small" style={{ padding: 8 }}>
            <div>{longDate(p.date)}</div><div>{label}: {money(p.value)}</div>
            <div>Round-ups added: {money(p.added)}</div>
            {p.carried === "true" && <div className="muted">Price carried from the last trading day</div>}
          </div>);
        }} />
        {active !== null && pts[active] && <ReferenceLine x={pts[active].date} stroke="var(--ink2)" strokeWidth={1} />}
        <Area type="linear" dataKey="v" name={label} stroke={color} strokeWidth={2.5} fill={`url(#${gid})`} dot={false} isAnimationActive={false} />
        <Line type="linear" dataKey="a" name="Round-ups added so far" stroke="var(--added)" strokeDasharray="6 5" strokeWidth={2} dot={false} isAnimationActive={false} />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
