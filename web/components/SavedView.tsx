"use client";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { COPY } from "@/lib/copy";
import { longDate, money } from "@/lib/format";
import { deleteSaved, listSaved, type SavedScenario } from "@/lib/saved";
import type { SimulateRequest, Strategy, Style } from "@/lib/types";
import { useAuth } from "./AuthContext";
import { ErrorNotice } from "./Chrome";
import { Icon } from "./Icon";
import { Skeleton } from "./Skeleton";
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
  const keep = useRef<HTMLButtonElement>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  const [announce, setAnnounce] = useState("");

  const load = useCallback(async () => {
    if (!session) return;
    setError("");
    try { setItems(await listSaved(session.token)); }
    catch (e) { setError((e as { code?: string }).code === "AUTH" ? COPY.errors.sessionExpired : (e as Error).message); }
  }, [session]);
  useEffect(() => { load(); }, [load]);
  useEffect(() => {                              // the safe choice ("Keep it") gets focus when the dialog opens
    if (confirm) { dialog.current?.showModal(); keep.current?.focus(); } else dialog.current?.close();
  }, [confirm]);

  function open(x: SavedScenario) {
    const r = x.scenario_results[0];
    if (!r) return;
    const c = x.config;
    const request: SimulateRequest = { scenario_id: c.scenario_id, style: c.style as Style, start: c.start, end: c.end,
      strategy: c.strategy as Strategy, reinvest: c.reinvest, ...(c.typical ? { typical: c.typical } : {}) };
    setRun({ request, sample: true, savedName: x.name, response: { result: r.result, meta: {
      engine_version: r.engine_version, model_version: r.model_version, scenario_id: c.scenario_id, style: c.style as Style,
      scenario_seed: r.scenario_seed, market_checksum: r.market_checksum, input_checksum: r.input_checksum,
      label: COPY.label } } });
    router.push("/results");
  }
  async function remove() {
    if (!confirm || !session) return;
    const name = confirm.name;
    try {                                      // reviewer L10: say what happened and put focus somewhere sensible
      await deleteSaved(session.token, confirm.id); setConfirm(null); await load();
      setAnnounce(COPY.deleted(name)); heading.current?.focus();
    }
    catch (e) { setConfirm(null); setError((e as Error).message); }
  }

  return (<>
    <h1 ref={heading} tabIndex={-1}>Saved scenarios</h1>
    <p role="status" className={announce ? "success" : "visually-hidden"}>{announce}</p>
    <p className="muted">{COPY.savedIntro}</p>
    {!ready ? (<><p role="status">Loading…</p><div className="saved-grid" aria-hidden="true">{[0, 1, 2].map((i) => <div key={i} className="card saved-card"><Skeleton height={22} width="60%" /><Skeleton height={14} /><Skeleton height={14} width="80%" /></div>)}</div></>)
      : mode === "off" ? <section className="card empty"><span className="empty-icon"><Icon name="bookmark" size={32} /></span><p>{COPY.signInNotSetUp}</p></section>
      : !session ? (<section className="card empty"><span className="empty-icon"><Icon name="bookmark" size={32} /></span><h2>Sign in to see saved scenarios</h2>
          <SignInForm intro={COPY.signedOutSaved} /></section>)
      : (<>
        {error && <ErrorNotice message={error} />}
        {items && items.length === 0 && (<section className="card empty"><span className="empty-icon"><Icon name="bookmark" size={32} /></span><h2>Nothing saved yet</h2>
          <p className="muted">Run a simulation, then choose <strong>Save</strong> to keep it here.</p>
          <a className="btn btn-primary" href="/">Start a simulation</a></section>)}
        {items && items.length > 0 && (<ul className="saved-grid">{items.map((x) => {
          const s = x.scenario_results[0]?.result.summary;
          return (<li className="card saved-card" key={x.id}><div>
            <h2><span className="stat-icon"><Icon name="bookmark" size={20} /></span><bdi>{x.name}</bdi></h2>
            <p className="meta">Synthetic scenario: {x.config.scenario_id.replace(/-/g, " ")} ·{" "}
              {x.config.style === "broad" ? "broad-market style" : "dividend style"} · {COPY.strategy[x.config.strategy]} ·{" "}
              {COPY.dividends(x.config.reinvest).toLowerCase()}</p>
            {s && <p className="small" style={{ margin: "8px 0 0" }}>Round-ups added {money(s.contributed)} · value at end{" "}
              {money(s.ending_value)} on {longDate(s.as_of)} · saved {longDate(x.created_at.slice(0, 10))}</p>}</div>
            <div className="btn-row"><button className="btn" type="button" onClick={() => open(x)} aria-label={`Open ${x.name}`}><Icon name="open" size={18} /> Open</button>
              <button className="btn" type="button" onClick={() => setConfirm(x)} aria-haspopup="dialog" aria-label={`Delete ${x.name}`}><Icon name="trash" size={18} /> Delete</button></div>
          </li>);})}</ul>)}
      </>)}
    <dialog ref={dialog} aria-labelledby="del-h" onClose={() => setConfirm(null)}>
      <div className="dialog-head"><h2 id="del-h">Delete scenario</h2></div>
      <p>Delete &ldquo;<bdi>{confirm?.name}</bdi>&rdquo;? This removes the scenario and its results. It can&rsquo;t be undone.</p>
      <div className="btn-row"><button className="btn btn-primary" type="button" onClick={remove}>Delete</button>
        <button className="btn" type="button" ref={keep} onClick={() => setConfirm(null)}>Keep it</button></div>
    </dialog>
  </>);
}
