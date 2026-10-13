"use client";
// Drawing only (lazy-loaded): converts engine strings to numbers for line coordinates and axis positions.
// Every figure a person reads in the tooltip is the original API string.
import { useMemo } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { longDate, money } from "@/lib/format";
import type { Point } from "@/lib/types";

export default function ChartCanvas({ pts, title, summary, top, color, label }:
  { pts: Point[]; title: string; summary: string; top: number; color: string; label: string }) {
  const data = useMemo(() => pts.map((p, i) => ({ i, date: p.date, v: Number(p.value), a: Number(p.added) })), [pts]);
  // one x-axis tick per year (first chart point of each year), or per quarter for short ranges
  const ticks = useMemo(() => {
    const short = pts.length < 400;
    const key = (d: string) => (short ? `${d.slice(0, 4)}-${Math.floor((Number.parseInt(d.slice(5, 7), 10) - 1) / 3)}` : d.slice(0, 4));
    return pts.filter((p, i) => i === 0 || key(p.date) !== key(pts[i - 1].date)).map((p) => p.date);
  }, [pts]);
  const tickLabel = (d: string) => (pts.length < 400
    ? new Date(`${d}T00:00:00Z`).toLocaleDateString("en-US", { month: "short", year: "2-digit", timeZone: "UTC" }) : d.slice(0, 4));
  const desc = summary;
  return (
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 8 }} title={title}
            desc={desc}>
            <CartesianGrid vertical={false} stroke="var(--line)" />
            <XAxis dataKey="date" ticks={ticks} tickFormatter={tickLabel} minTickGap={16} interval="preserveStartEnd"
              stroke="var(--control)" tick={{ fill: "var(--ink-2)", fontSize: 12 }} />
            <YAxis domain={[0, top]} tickFormatter={(n: number) => `$${n.toLocaleString("en-US")}`}
              stroke="var(--control)" tick={{ fill: "var(--ink-2)", fontSize: 12 }} width={64} />
            <Tooltip content={({ active, payload }) => {
              if (!active || !payload?.length) return null;
              const p = pts[(payload[0].payload as { i: number }).i];
              return (<div className="card small" style={{ padding: 8 }}>
                <div>{longDate(p.date)}</div><div>{label}: {money(p.value)}</div>
                <div>Round-ups added: {money(p.added)}</div>
                {p.carried === "true" && <div className="muted">Price carried from the last trading day</div>}
              </div>);
            }} />
            <Line type="linear" dataKey="a" name="Round-ups added so far" stroke="var(--added)" strokeDasharray="5 4"
              strokeWidth={2} dot={false} isAnimationActive={false} />
            <Line type="linear" dataKey="v" name={label} stroke={color} strokeWidth={2} dot={false} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
  );
}
