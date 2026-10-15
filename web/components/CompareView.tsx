"use client";
import Link from "next/link";
import { useRef, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { COPY } from "@/lib/copy";
import { count, dateRange, isNegative, money, signedMoney, unsignedMoney } from "@/lib/format";
import type { Strategy } from "@/lib/types";
import { Disclaimer, ErrorNotice } from "./Chrome";
import { Icon } from "./Icon";
import { KeyPoints } from "./KeyPoints";
import { DipSentence } from "./ResultParts";
import { useRun } from "./RunContext";
import { useRateLimitWait } from "./useRateLimitWait";
import { chartTop, ValueChart } from "./ValueChart";

const STRATS: Strategy[] = ["threshold", "next_session", "weekly", "monthly"];

function SidePicker({ side, value, onChange }: { side: "A" | "B"; value: { strategy: Strategy; reinvest: boolean };
  onChange: (v: { strategy: Strategy; reinvest: boolean }) => void }) {
  return (
    <fieldset className="card" style={{ marginBottom: 0 }}>
      <legend style={{ fontSize: 18 }}>{side} <span className="small muted">How round-ups are invested</span></legend>
      {/* Radio rows, not a dropdown: a dropdown cannot wrap, so its label was clipped whenever the platform's fonts ran a
          few pixels wider (279 px on macOS, 284 px under Linux in CI). Text in a row wraps, so it can never be cut off. */}
      <div className="radio-list">
        {STRATS.map((s) => (
          <label className="radio-row" key={s}><input type="radio" name={`strategy-${side}`} value={s} checked={value.strategy === s}
            onChange={() => onChange({ ...value, strategy: s })} /><span>{COPY.strategy[s]}</span></label>))}
      </div>
      <label className="switch"><input type="checkbox" checked={value.reinvest}
        onChange={(e) => onChange({ ...value, reinvest: e.target.checked })} /><span>Reinvest dividends</span></label>
    </fieldset>
  );
}

export function CompareView() {
  const { run, compare, setCompare } = useRun();
  const [a, setA] = useState({ strategy: "threshold" as Strategy, reinvest: true });
  const [b, setB] = useState({ strategy: "monthly" as Strategy, reinvest: false });
  const [error, setError] = useState<ApiError | null>(null);
  const [busy, setBusy] = useState(false);
  const inFlight = useRef(false);                 // reviewer L1: rapid clicks send one request
  const [coolingDown, noteRateLimit] = useRateLimitWait();     // reviewer L2

  if (!run) {
    return (<section className="card empty"><span className="empty-icon"><Icon name="layers" size={32} /></span><h1>Compare two ways of investing</h1>
      <p className="muted">{COPY.compareEmpty}</p>
      <Link className="btn btn-primary" href="/">Set up a simulation</Link></section>);
  }
  const { strategy: _s, reinvest: _r, ...base } = run.request;
  async function go(e: React.FormEvent) {
    e.preventDefault();
    if (inFlight.current || coolingDown) return;
    inFlight.current = true; setBusy(true); setError(null);
    try { setCompare({ request: { ...base, a, b }, response: await api.compare({ ...base, a, b }), sample: run!.sample }); }
    catch (err) { noteRateLimit(err as ApiError); setError(err as ApiError); } finally { inFlight.current = false; setBusy(false); }
  }
  const C = compare?.response;
  const rows: [string, string, string, string][] = C ? [
    ["Round-ups added", money(C.a.summary.contributed), money(C.b.summary.contributed), COPY.sameForBoth],
    ["Value at end", money(C.a.summary.ending_value), money(C.b.summary.ending_value), signedMoney(C.difference.ending_value)],
    ["Growth on round-ups", signedMoney(C.a.summary.gain), signedMoney(C.b.summary.gain), signedMoney(C.difference.gain)],
    ["Dividends (simulated)", money(C.a.summary.dividends_earned), money(C.b.summary.dividends_earned), signedMoney(C.difference.dividends_earned)],
    ["Round-ups waiting to be invested", money(C.a.summary.roundups_waiting), money(C.b.summary.roundups_waiting), COPY.seeAB],
    ["Dividends kept as cash", money(C.a.summary.dividends_as_cash), money(C.b.summary.dividends_as_cash), COPY.seeAB],
    ["Times invested from round-ups", count(C.a.summary.roundup_buys), count(C.b.summary.roundup_buys), count(C.difference.roundup_buys, true)],
    ["Times invested from dividends", count(C.a.summary.dividend_buys), count(C.b.summary.dividend_buys), count(C.difference.dividend_buys, true)],
  ] : [];
  const top = C ? chartTop([...C.a.series, ...C.b.series]) : undefined;   // shared drawing scale
  const req = compare?.request;

  return (
    <div className="layout">
    <aside className="assumptions-rail-wrap"><KeyPoints headingId="cmp-key-points" /></aside>
    <div className="layout-main">
      <h1>Compare two ways of investing</h1>
      <p className="muted">Same {run.sample ? "sample " : ""}purchases, same synthetic scenario ({run.response.meta.scenario_id.replace(/-/g, " ")},
        {" "}{run.request.style === "broad" ? "broad-market style" : "dividend style"}, {dateRange(run.request.start, run.request.end)}).
        Only the settings below differ. {COPY.datesNote}</p>
      <form onSubmit={go}>
        <div className="pickers"><SidePicker side="A" value={a} onChange={setA} /><SidePicker side="B" value={b} onChange={setB} /></div>
        <button className="btn btn-primary" type="submit" disabled={busy || coolingDown}>{busy ? "Comparing…" : "Compare"}</button>
      </form>
      {error && <ErrorNotice message={error.message} requestId={error.requestId} />}
      {C && req && (<>
        <div style={{ marginTop: 24 }}><Disclaimer sample={compare!.sample} /></div>
        <div className="diff-summary" data-testid="diff-summary"><Icon name="info" size={24} />
          <p>{C.difference.ending_value === "0.00" ? COPY.diffSame : COPY.diffSummary(!isNegative(C.difference.ending_value), unsignedMoney(C.difference.ending_value))}</p></div>
        <div className="compare-grid">
          <div className="card"><h2 className="col-head"><span className="key" style={{ background: "var(--series-a)" }} aria-hidden="true" />A</h2>
            <p style={{ margin: 0 }}>{COPY.strategy[req.a.strategy]}. {COPY.dividends(req.a.reinvest)}.</p></div>
          <div className="card"><h2 className="col-head"><span className="key" style={{ background: "var(--series-b)" }} aria-hidden="true" />B</h2>
            <p style={{ margin: 0 }}>{COPY.strategy[req.b.strategy]}. {COPY.dividends(req.b.reinvest)}.</p></div>
        </div>
        <div className="table-scroll" style={{ maxHeight: "none" }} role="region" aria-label="Comparison table" tabIndex={0}>
          <table className="cmp-table"><caption className="visually-hidden">Results for A and B, and B minus A</caption>
            <thead><tr><th scope="col">Figure</th><th scope="col">A</th><th scope="col">B</th><th scope="col">B minus A</th></tr></thead>
            <tbody>{rows.map(([k, x, y, z]) => <tr key={k}><th scope="row">{k}</th><td data-label="A">{x}</td>
              <td data-label="B">{y}</td><td data-label="B minus A">{z}</td></tr>)}</tbody></table></div>
        <p className="small muted" style={{ marginTop: 8 }}>{COPY.compareNote}</p>
        <h2 style={{ marginTop: 24 }}>Value over time</h2>
        <div className="multiples">
          <div className="card"><ValueChart result={C.a} title={`A: ${COPY.strategy[req.a.strategy].toLowerCase()}`} yTop={top} small label="A" level={3} /></div>
          <div className="card"><ValueChart result={C.b} title={`B: ${COPY.strategy[req.b.strategy].toLowerCase()}`} yTop={top} small label="B" color="var(--series-b)" level={3} /></div>
        </div>
        <DipSentence dip={C.a.summary.deepest_dip} who="A" />
        <DipSentence dip={C.b.summary.deepest_dip} who="B" />
        <p className="small muted">Both charts use the same scale. The dashed line is the round-ups added so far.</p>
      </>)}
    </div></div>
  );
}
