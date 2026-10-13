"use client";
import Link from "next/link";
import { useState } from "react";
import { api, ApiError } from "@/lib/api";
import { COPY } from "@/lib/copy";
import { count, longDate } from "@/lib/format";
import { useAuth } from "./AuthContext";
import { Disclaimer, ErrorNotice } from "./Chrome";
import { KeyPoints } from "./KeyPoints";
import { CashSentence, DipSentence, Headline, StatTiles } from "./ResultParts";
import { useRun } from "./RunContext";
import { ValueChart } from "./ValueChart";

export function ResultsView() {
  const { run } = useRun();
  const { session, mode } = useAuth();
  const [saving, setSaving] = useState(false);
  const [name, setName] = useState("");
  const [keepTx, setKeepTx] = useState(false);
  const [saved, setSaved] = useState<string | null>(null);
  const [error, setError] = useState<ApiError | null>(null);

  if (!run) {
    return (<section className="card empty"><h1>No results yet</h1><p className="muted">Run a simulation first.</p>
      <Link className="btn btn-primary" href="/">Set up a simulation</Link></section>);
  }
  const { response, request, sample } = run;
  const r = response.result, m = response.meta;
  const scenarioName = m.scenario_id.replace(/-/g, " ").replace(/^./, (c) => c.toUpperCase());

  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (!session) return;
    setError(null);
    try {
      await api.save(request, name.trim(), keepTx, session.token);
      setSaved(name.trim()); setSaving(false);
    } catch (err) {
      const e2 = err as ApiError;
      setError(e2.status === 401 ? new ApiError(401, "AUTH_INVALID", COPY.errors.sessionExpired) : e2);
    }
  }

  return (
    <div className="layout"><div>
      <h1>{sample ? "Your sample round-ups in a made-up market" : "Your round-ups in a made-up market"}</h1>
      {run.savedName && <p className="success">Saved scenario: {run.savedName}</p>}
      <ul className="chips" aria-label="Simulation settings">
        <li>{count(r.transactions_used)} {sample ? "sample " : ""}purchases</li>
        <li>{scenarioName}, {m.style === "broad" ? "broad-market style" : "dividend style"}</li>
        <li>{COPY.strategy[request.strategy]}</li><li>{COPY.dividends(request.reinvest)}</li>
        <li>{longDate(request.start)} – {longDate(request.end)}</li>
        <li><Link href="/">Edit settings</Link></li>
      </ul>
      <Disclaimer sample={sample} />
      {r.summary.contributed === "0.00" ? <p className="headline">{COPY.wholeDollar}</p> : <Headline result={r} sample={sample} />}
      <StatTiles result={r} sample={sample} />
      <ValueChart result={r} title="Value over time" />
      <DipSentence dip={r.summary.deepest_dip} />
      <CashSentence result={r} />

      <h2 style={{ marginTop: 24 }}>Questions about these numbers</h2>
      <p className="small muted" data-testid="explainer-placeholder"><strong>Coming later:</strong> {COPY.explainer}</p>

      <div className="btn-row" style={{ marginTop: 24 }}>
        {session ? (!saving && !saved && <button className="btn btn-primary" type="button" onClick={() => setSaving(true)}>Save this scenario</button>)
          : mode !== "off" && <Link className="btn btn-primary" href="/saved">Sign in to save</Link>}
        <Link className="btn" href="/compare">Compare with another way of investing</Link>
      </div>
      {saving && (
        <form className="inline-form card" style={{ marginTop: 16 }} onSubmit={save}>
          <div className="field"><label htmlFor="save-name">Name for this scenario</label>
            <input id="save-name" value={name} maxLength={80} onChange={(e) => setName(e.target.value)} required /></div>
          <label className="switch" style={{ marginTop: 0 }}><input type="checkbox" checked={keepTx} onChange={(e) => setKeepTx(e.target.checked)} />
            <span>Also save the purchases (dates and amounts only, never merchant names)</span></label>
          <div className="btn-row"><button className="btn btn-primary" type="submit" disabled={!name.trim()}>Save</button>
            <button className="btn" type="button" onClick={() => setSaving(false)}>Cancel</button></div>
        </form>)}
      {saved && <p className="success" role="status">Saved as &ldquo;{saved}&rdquo;. <Link href="/saved">See saved scenarios</Link></p>}
      {error && <ErrorNotice message={error.message} requestId={error.requestId} />}

      <details className="tech"><summary>Technical details</summary>
        <p className="small muted">Scenario {m.scenario_id}, seed {m.scenario_seed}, {m.model_version}; engine {m.engine_version};
          input checksum {m.input_checksum}. These let anyone reproduce the exact numbers.</p></details>
    </div>
    <aside className="assumptions-rail-wrap"><KeyPoints /></aside></div>
  );
}
