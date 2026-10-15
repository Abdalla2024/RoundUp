"use client";
import Link from "next/link";
import { useRef, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { COPY } from "@/lib/copy";
import { count, counted, dateRange, money } from "@/lib/format";
import type { SimulateRequest } from "@/lib/types";
import { useAuth } from "./AuthContext";
import { Disclaimer, ErrorNotice } from "./Chrome";
import { KeyPoints } from "./KeyPoints";
import { CashSentence, DipSentence, Headline, StatTiles } from "./ResultParts";
import { useRun } from "./RunContext";
import { SignInForm } from "./SignIn";
import { ValueChart } from "./ValueChart";

function purchasesSetting(req: SimulateRequest, savedName?: string): string {
  if (req.typical) return `typical spending, ${req.typical.per_week} purchases a week, average round-up ${money(req.typical.average_roundup)}`;
  if (req.generate) return `purchase list number ${req.generate.seed}, up to ${req.generate.max_per_day} purchases a day`;
  return savedName ? "purchases as saved" : "purchases from your file";
}

export function ResultsView() {
  const { run } = useRun();
  const { session, mode } = useAuth();
  const [saving, setSaving] = useState(false);
  const [inFlight, setInFlight] = useState(false);
  const busy = useRef(false);                       // guards a double click before React re-renders (reviewer M2)
  const [signIn, setSignIn] = useState(false);
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
  const canSave = !run.savedName && !saved;

  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (!session || busy.current) return;
    busy.current = true; setInFlight(true); setError(null);
    try {
      await api.save(request, name.trim(), keepTx, session.token);
      setSaved(name.trim()); setSaving(false);
    } catch (err) {
      const e2 = err as ApiError;
      setError(e2.status === 401 ? new ApiError(401, "AUTH_INVALID", COPY.errors.sessionExpired) : e2);
    } finally { busy.current = false; setInFlight(false); }
  }

  return (
    <div className="layout">
    <aside className="assumptions-rail-wrap"><KeyPoints /></aside>
    <div className="layout-main">
      <h1>{sample ? "Your sample round-ups in a made-up market" : "Your round-ups in a made-up market"}</h1>
      {run.savedName && <p className="success">Saved scenario: <bdi>{run.savedName}</bdi></p>}
      <ul className="chips" aria-label="Simulation settings">
        <li>{counted(r.transactions_used, sample ? "sample purchase" : "purchase", sample ? "sample purchases" : "purchases")}</li>
        <li>{scenarioName}, {m.style === "broad" ? "broad-market style" : "dividend style"}</li>
        <li>{COPY.strategy[request.strategy]}</li><li>{COPY.dividends(request.reinvest)}</li>
        <li>{dateRange(request.start, request.end)}</li>
        <li className="chip-link"><Link href="/">Edit settings</Link></li>
      </ul>
      {request.typical && <p className="muted small" data-testid="typical-note">{COPY.typicalNote(String(request.typical.per_week), money(request.typical.average_roundup))}</p>}
      <Disclaimer sample={sample} />
      {r.summary.contributed === "0.00"
        ? <p className="headline">{r.transactions_used === "0" ? COPY.noneInWindow : COPY.wholeDollar}</p>
        : <Headline result={r} sample={sample} />}
      <StatTiles result={r} sample={sample} />
      {r.transactions_ignored !== "0" && <p className="muted" data-testid="not-counted">{COPY.notCounted(count(r.transactions_ignored))}</p>}
      <ValueChart result={r} title="Value over time" />
      <DipSentence dip={r.summary.deepest_dip} />
      <CashSentence result={r} />

      <h2 style={{ marginTop: 24 }}>Questions about these numbers</h2>
      <p className="small muted" data-testid="explainer-placeholder"><strong>Coming later:</strong> {COPY.explainer}</p>

      <div className="btn-row" style={{ marginTop: 24 }}>
        {session ? (canSave && !saving && <button className="btn btn-primary" type="button" onClick={() => setSaving(true)}>Save this scenario</button>)
          : mode !== "off" && canSave && !signIn &&
            <button className="btn btn-primary" type="button" onClick={() => setSignIn(true)}>Sign in to save</button>}
        <Link className="btn" href="/compare">Compare with another way of investing</Link>
      </div>
      {!session && signIn && (
        <section className="card" style={{ marginTop: 16 }} aria-labelledby="signin-h">
          <h2 id="signin-h" style={{ fontSize: 18 }}>Sign in to save</h2>
          <SignInForm intro={COPY.signedOutSaved} sentMessage={COPY.linkSentKeepTab} autoFocus />
        </section>)}
      {session && saving && (
        <form className="inline-form card" style={{ marginTop: 16 }} onSubmit={save}>
          <div className="field"><label htmlFor="save-name">Name for this scenario</label>
            <input id="save-name" value={name} maxLength={80} onChange={(e) => setName(e.target.value)} required
              autoFocus /></div>
          <label className="switch" style={{ marginTop: 0 }}><input type="checkbox" checked={keepTx} onChange={(e) => setKeepTx(e.target.checked)} />
            <span>Also save the purchases (dates and amounts only, never merchant names)</span></label>
          <div className="btn-row"><button className="btn btn-primary" type="submit" disabled={!name.trim() || inFlight}>
            {inFlight ? "Saving…" : "Save"}</button>
            <button className="btn" type="button" onClick={() => setSaving(false)}>Cancel</button></div>
        </form>)}
      {saved && <p className="success" role="status">Saved as &ldquo;<bdi>{saved}</bdi>&rdquo;. <Link href="/saved">See saved scenarios</Link></p>}
      {error && <ErrorNotice message={error.message} requestId={error.requestId} />}

      <details className="tech"><summary>Technical details</summary>
        <p className="small muted">Scenario {m.scenario_id} ({m.style === "broad" ? "broad-market style" : "dividend style"}),
          scenario seed {m.scenario_seed}, model {m.model_version}; engine {m.engine_version}; input checksum {m.input_checksum}.
          Settings: {purchasesSetting(request, run.savedName)}; {dateRange(request.start, request.end).replace(" – ", " to ")};
          {" "}{COPY.strategy[request.strategy]}; {COPY.dividends(request.reinvest).toLowerCase()}. The same settings and
          purchases give exactly these numbers again.</p></details>
    </div></div>
  );
}
