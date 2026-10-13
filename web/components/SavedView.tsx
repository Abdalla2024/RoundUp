"use client";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { COPY } from "@/lib/copy";
import { longDate, money } from "@/lib/format";
import { deleteSaved, listSaved, type SavedScenario } from "@/lib/saved";
import type { SimulateRequest, Strategy, Style } from "@/lib/types";
import { useAuth } from "./AuthContext";
import { ErrorNotice } from "./Chrome";
import { useRun } from "./RunContext";
import { SignInForm } from "./SignIn";

export function SavedView() {
  const { session, mode, ready } = useAuth();
  const { setRun } = useRun();
  const router = useRouter();
  const [items, setItems] = useState<SavedScenario[] | null>(null);
  const [error, setError] = useState("");
  const [confirm, setConfirm] = useState<SavedScenario | null>(null);
  const dialog = useRef<HTMLDialogElement>(null);

  const load = useCallback(async () => {
    if (!session) return;
    setError("");
    try { setItems(await listSaved(session.token)); }
    catch (e) { setError((e as { code?: string }).code === "AUTH" ? COPY.errors.sessionExpired : (e as Error).message); }
  }, [session]);
  useEffect(() => { load(); }, [load]);
  useEffect(() => { if (confirm) dialog.current?.showModal(); else dialog.current?.close(); }, [confirm]);

  function open(x: SavedScenario) {
    const r = x.scenario_results[0];
    if (!r) return;
    const c = x.config;
    const request: SimulateRequest = { scenario_id: c.scenario_id, style: c.style as Style, start: c.start, end: c.end,
      strategy: c.strategy as Strategy, reinvest: c.reinvest };
    setRun({ request, sample: true, savedName: x.name, response: { result: r.result, meta: {
      engine_version: r.engine_version, model_version: r.model_version, scenario_id: c.scenario_id, style: c.style as Style,
      scenario_seed: r.scenario_seed, market_checksum: r.market_checksum, input_checksum: r.input_checksum,
      label: COPY.label } } });
    router.push("/results");
  }
  async function remove() {
    if (!confirm || !session) return;
    try { await deleteSaved(session.token, confirm.id); setConfirm(null); await load(); }
    catch (e) { setConfirm(null); setError((e as Error).message); }
  }

  return (<>
    <h1>Saved scenarios</h1>
    <p className="muted">{COPY.savedIntro}</p>
    {!ready ? <p role="status">Loading…</p>
      : mode === "off" ? <section className="card empty"><p>{COPY.signInNotSetUp}</p></section>
      : !session ? (<section className="card empty"><h2>Sign in to see saved scenarios</h2>
          <SignInForm intro={COPY.signedOutSaved} /></section>)
      : (<>
        {error && <ErrorNotice message={error} />}
        {items && items.length === 0 && (<section className="card empty"><h2>Nothing saved yet</h2>
          <p className="muted">Run a simulation, then choose <strong>Save</strong> to keep it here.</p>
          <a className="btn btn-primary" href="/">Start a simulation</a></section>)}
        {items && items.length > 0 && (<ul className="saved-list">{items.map((x) => {
          const s = x.scenario_results[0]?.result.summary;
          return (<li className="card saved-item" key={x.id}><div>
            <h2 style={{ fontSize: 16, margin: "0 0 4px" }}>{x.name}</h2>
            <p className="small muted" style={{ margin: 0 }}>Synthetic scenario: {x.config.scenario_id.replace(/-/g, " ")} ·{" "}
              {x.config.style === "broad" ? "broad-market style" : "dividend style"} · {COPY.strategy[x.config.strategy]} ·{" "}
              {COPY.dividends(x.config.reinvest).toLowerCase()}</p>
            {s && <p className="small" style={{ margin: "4px 0 0" }}>Round-ups added {money(s.contributed)} · value at end{" "}
              {money(s.ending_value)} on {longDate(s.as_of)} · saved {longDate(x.created_at.slice(0, 10))}</p>}</div>
            <div className="btn-row"><button className="btn" type="button" onClick={() => open(x)} aria-label={`Open ${x.name}`}>Open</button>
              <button className="btn" type="button" onClick={() => setConfirm(x)} aria-haspopup="dialog" aria-label={`Delete ${x.name}`}>Delete</button></div>
          </li>);})}</ul>)}
      </>)}
    <dialog ref={dialog} aria-labelledby="del-h" onClose={() => setConfirm(null)}>
      <div className="dialog-head"><h2 id="del-h">Delete scenario</h2></div>
      <p>Delete &ldquo;{confirm?.name}&rdquo;? This removes the scenario and its results. It can&rsquo;t be undone.</p>
      <div className="btn-row"><button className="btn btn-primary" type="button" onClick={remove}>Delete</button>
        <button className="btn" type="button" autoFocus onClick={() => setConfirm(null)}>Keep it</button></div>
    </dialog>
  </>);
}
