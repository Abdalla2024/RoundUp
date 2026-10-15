"use client";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { COPY } from "@/lib/copy";
import { csvHeader } from "@/lib/csvHeader";
import { count, longDate } from "@/lib/format";
import type { Mapping, ParseResponse, ScenariosResponse, SimulateRequest, Strategy, Style, TransactionIn } from "@/lib/types";
import { ErrorNotice } from "./Chrome";
import { Icon, type IconName } from "./Icon";
import { ProgressRail } from "./ProgressRail";
import { Skeleton } from "./Skeleton";
import { Sparkline } from "./Sparkline";
import { useRun, type SetupDraft } from "./RunContext";
import { useRateLimitWait } from "./useRateLimitWait";

const MAX_CSV_CHARS = 2_000_000;
const STRATEGY_ICON: Record<Strategy, IconName> = { threshold: "coins", next_session: "clock", weekly: "repeat", monthly: "calendar" };
const STRATEGIES: [Strategy, string, string][] = [
  ["threshold", "When they reach $5", "Saved-up round-ups are invested once they add up to $5."],
  ["next_session", "After every purchase day", "Each day’s round-ups are invested on the next trading day."],
  ["weekly", "Once a week", "The week’s round-ups are invested after Sunday."],
  ["monthly", "Once a month", "The month’s round-ups are invested after the month ends."],
];
const CONVENTIONS: [string, string][] = [
  ["debits_positive", "Purchases are positive numbers"], ["debits_negative", "Purchases are negative numbers"],
  ["separate_columns", "Money out and money in columns"], ["type_column", "A column says debit or credit"],
];
type Col = "date" | "amount" | "debit" | "credit" | "type" | "status" | "description";
const COL_LABEL: Record<Col, string> = { date: "Date column", amount: "Amount column", debit: "Money out column",
  credit: "Money in column", type: "Debit or credit column", status: "Status column (optional)", description: "Description column (optional)" };
const SLASH_DATE = /(^|[,"\s])\d{1,2}\/\d{1,2}\/\d{4}([,"\s]|$)/m;

const DEFAULTS: SetupDraft = { source: "typical", perWeek: "10", avgRoundup: "0.50", scenarioId: "crash-and-recovery",
  style: "broad", strategy: "threshold", reinvest: true, start: "2015-01-02", end: "2024-12-31", csv: null,
  columns: [], mapping: {}, convention: "", convNote: "", countUnrecognised: false, parsed: null, slashDates: false };

/** Which column pickers a sign option needs (reviewer M4). */
function visibleColumns(convention: string, mapping: Mapping): Col[] {
  if (convention === "separate_columns") return ["date", "debit", "credit", "status", "description"];
  if (convention === "type_column") return ["date", "amount", "type", "status", "description"];
  if (convention) return ["date", "amount", "status", "description"];
  return ["date", "amount", ...(["debit", "credit", "type"] as Col[]).filter((k) => mapping[k]), "status", "description"];
}

/** A weekly count: 1 to 60, written as whole-number text. Returns the number, or 0 when the text is not valid. */
const weeklyCount = (t: string): number => {
  if (!/^[0-9]{1,2}$/.test(t)) return 0;
  const n = Number.parseInt(t, 10);
  return n >= 1 && n <= 60 ? n : 0;
};

export function SetupForm() {
  const router = useRouter();
  const { setRun, draft, setDraft } = useRun();
  const [f, setF] = useState<SetupDraft>(draft ?? DEFAULTS);       // reviewer M1: settings survive leaving the page
  const set = (patch: Partial<SetupDraft>) => setF((cur) => ({ ...cur, ...patch }));
  useEffect(() => { setDraft(f); }, [f, setDraft]);
  const [scen, setScen] = useState<ScenariosResponse | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [busy, setBusy] = useState(false);
  const [adjustOpen, setAdjustOpen] = useState(false);
  const [lastGood, setLastGood] = useState(weeklyCount(draft?.perWeek ?? "") ? draft!.perWeek : "10");
  const [coolingDown, noteRateLimit] = useRateLimitWait();     // reviewer L2
  const errorRef = useRef<HTMLDivElement>(null);

  useEffect(() => { api.scenarios().then(setScen).catch((e) => setError(e as ApiError)); }, []);
  useEffect(() => {
    if (!error) return;
    // an error about the sign box moves focus to that box (the banner is read out as an alert either way)
    if (error.fields.includes("sign_convention")) document.getElementById("convention")?.focus();
    else errorRef.current?.focus();
  }, [error]);

  const range = scen?.scenarios.find((s) => s.id === f.scenarioId)?.styles.find((s) => s.style === f.style);
  const invalid = (k: string) => Boolean(error?.fields.some((x) => x === k || x.startsWith(k + ".")));
  const cols = visibleColumns(f.convention, f.mapping);
  const sentMapping = (): Mapping => Object.fromEntries(cols.filter((k) => f.mapping[k]).map((k) => [k, f.mapping[k]]));

  // The file's first and last usable dates (ISO text, compared as text) for the check step (reviewer H2)
  const fileDates = f.parsed?.transactions.filter((t) => t.problem === null && t.posted_date).map((t) => t.posted_date!).sort() ?? [];
  const first = fileDates[0], last = fileDates[fileDates.length - 1];
  const outside = Boolean(first && (first < f.start || last > f.end));
  const overlaps = Boolean(range && first && first <= range.end && last >= range.start);

  async function onFile(file: File | undefined) {
    set({ parsed: null, columns: [], csv: null, slashDates: false }); setError(null);
    if (!file) return;
    const text = await file.text();
    if (text.length > MAX_CSV_CHARS) {
      setError(new ApiError(413, "PAYLOAD_TOO_LARGE", "This file is too large. The limit is 2 MB or 20,000 rows."));
      return;
    }
    if (!text.trim()) { setError(new ApiError(422, "CSV_INVALID", COPY.emptyFile)); return; }
    const columns = csvHeader(text);
    if (columns.length === 1 && columns[0].includes(";")) { setError(new ApiError(422, "CSV_INVALID", COPY.semicolons)); return; }
    if (columns.length === 1 && columns[0].includes("\t")) { setError(new ApiError(422, "CSV_INVALID", COPY.tabs)); return; }
    const guess = (re: RegExp) => columns.find((c) => re.test(c)) ?? null;
    const mapping: Mapping = {
      date: guess(/date/i), amount: guess(/amount/i), description: guess(/desc|merchant|name|memo/i),
      status: guess(/^(status|transaction status|state)$/i),
      debit: guess(/^(debit|debits|withdrawals?|money out|paid out|amount out)$/i),
      credit: guess(/^(credit|credits|deposits?|money in|paid in|amount in)$/i),
      type: guess(/^(type|transaction type|debit\/credit|dr\/cr|cr\/dr)$/i) };
    // R-1.3: a layout is chosen for you only when the column names make it plain (two money columns, or a
    // debit/credit column beside the amount), and the page says so. A single signed column is never guessed.
    let convention = "", convNote = "";
    if (mapping.debit && mapping.credit && mapping.debit !== mapping.credit) {
      convention = "separate_columns"; convNote = COPY.signingChosenBecause(mapping.debit, mapping.credit);
    } else if (mapping.type && mapping.amount && mapping.type !== mapping.amount) {
      convention = "type_column"; convNote = COPY.signingChosenBecauseType(mapping.type);
    }
    set({ csv: text, columns, slashDates: SLASH_DATE.test(text), mapping, convention, convNote });
  }

  async function checkFile() {
    if (!f.csv) return;
    const chosen = cols.filter((k) => f.mapping[k]);
    const dup = chosen.filter((k) => chosen.some((j) => j !== k && f.mapping[j] === f.mapping[k]));
    if (dup.length) { setError(new ApiError(422, "INVALID_INPUT", COPY.sameColumn, dup.map((k) => `mapping.${k}`))); return; }
    if (!f.convention) { setError(new ApiError(422, "INVALID_INPUT", COPY.chooseSigning, ["sign_convention"])); return; }   // R-1.3
    setBusy(true); setError(null);
    try {
      const res = await api.parse(f.csv, sentMapping(), f.convention || null);
      set({ parsed: res });
    } catch (e) {
      const err = e as ApiError;
      noteRateLimit(err);
      setError(err.code === "SIGN_CONVENTION_REQUIRED"
        ? new ApiError(422, err.code, COPY.chooseSigning, ["sign_convention"], null, err.requestId) : err);
    } finally { setBusy(false); }
  }

  function applyFileDates() {
    if (!range || !first) return;
    set({ start: first > range.start ? first : range.start, end: last < range.end ? last : range.end });
  }

  async function onSubmit(ev: React.FormEvent) {
    ev.preventDefault();
    if (busy || coolingDown) return;
    setError(null);
    let req: SimulateRequest = { scenario_id: f.scenarioId, style: f.style, start: f.start, end: f.end,
      strategy: f.strategy, reinvest: f.reinvest };
    if (f.source === "typical") {
      const n = weeklyCount(f.perWeek);                                                    // whole numbers only; "1e1" and "5.5" fail the pattern
      if (n === 0) { setError(new ApiError(422, "INVALID_INPUT", COPY.perWeekError, ["typical.per_week"])); return; }
      if (!/^0\.(0[1-9]|[1-9][0-9])$/.test(f.avgRoundup)) {                                // text such as 0.50; sent exactly as typed
        setAdjustOpen(true);
        setError(new ApiError(422, "INVALID_INPUT", COPY.averageError, ["typical.average_roundup"])); return;
      }
      req = { ...req, typical: { per_week: n, average_roundup: f.avgRoundup } };
    } else {
      if (!f.parsed) { setError(new ApiError(422, "INVALID_INPUT", "Upload a CSV file and check it first.")); return; }
      const txs: TransactionIn[] = f.parsed.transactions.filter((t) => t.problem === null && t.posted_date && t.amount)
        .map((t) => ({ posted_date: t.posted_date!, amount: t.amount!, direction: t.direction,
          status: t.status === "unrecognised" && f.countUnrecognised ? ("posted" as const) : t.status, category: t.category }));   // R-1.4a: the user's decision
      if (txs.length === 0) { setError(new ApiError(422, "INVALID_INPUT", "No usable rows were found in this file.")); return; }
      req = { ...req, transactions: txs };
    }
    setBusy(true);
    try {
      const response = await api.simulate(req);
      setRun({ request: req, response, sample: f.source === "typical" });
      router.push("/results");
    } catch (e) { noteRateLimit(e as ApiError); setError(e as ApiError); } finally { setBusy(false); }
  }

  return (
    <form onSubmit={onSubmit} noValidate aria-describedby={error ? "form-error" : undefined}>
      <ProgressRail />
      {error && <div ref={errorRef} tabIndex={-1} id="form-error"><ErrorNotice message={error.message} requestId={error.requestId} /></div>}

      <fieldset className="step-card" id="step-1" data-step="1"><legend><span className="step-icon"><Icon name="wallet" /></span><span className="step-title"><span className="step">Step 1 of 4</span>Your purchases</span></legend>
        <p className="muted small">Round-ups come from purchases. Use sample spending, or upload a CSV export from your bank.
          Uploaded files are read in your session and not stored.</p>
        <div className="options">
          <label className="option choice"><input type="radio" name="source" value="typical" checked={f.source === "typical"}
            onChange={() => set({ source: "typical" })} /><span className="choice-icon"><Icon name="sliders" /></span><span className="title">{COPY.typicalTitle}</span>
            <span className="desc">{COPY.typicalDesc}</span></label>
          <label className="option choice"><input type="radio" name="source" value="upload" checked={f.source === "upload"}
            onChange={() => set({ source: "upload" })} /><span className="choice-icon"><Icon name="upload" /></span><span className="title">Upload a CSV</span>
            <span className="desc">You choose which columns hold the date and amount. Merchant names are never stored.</span></label>
        </div>
        {f.source === "typical" ? (<>
          <p className="muted small" style={{ marginTop: 12, marginBottom: 0 }}>{COPY.typicalEstimate}</p>
          <div className="typical">
            <div className="field"><label htmlFor="perweek" id="perweek-l">{COPY.perWeekLabel}</label>
              <div className="slider-row">
                <input type="range" min={1} max={60} step={1} aria-labelledby="perweek-l" aria-describedby="perweek-help"
                  value={weeklyCount(f.perWeek) ? f.perWeek : lastGood}
                  onChange={(e) => { setLastGood(e.target.value); set({ perWeek: e.target.value }); }} />
                <input id="perweek" className="number-box" inputMode="numeric" value={f.perWeek}
                  onChange={(e) => { set({ perWeek: e.target.value }); if (weeklyCount(e.target.value)) setLastGood(e.target.value); }}
                  aria-invalid={invalid("typical.per_week")} aria-describedby="perweek-help" />
              </div>
              <span id="perweek-help" className="small muted">{COPY.perWeekHint}</span></div>
            <details className="adjust" open={adjustOpen} onToggle={(e) => setAdjustOpen((e.currentTarget as HTMLDetailsElement).open)}>
              <summary>{COPY.adjustAverage}</summary>
              <p className="small muted">{COPY.adjustAverageBody}</p>
              <div className="field"><label htmlFor="avg">{COPY.averageLabel}</label>
                <input id="avg" inputMode="decimal" value={f.avgRoundup} onChange={(e) => set({ avgRoundup: e.target.value })}
                  aria-invalid={invalid("typical.average_roundup")} aria-describedby="avg-help" />
                <span id="avg-help" className="small muted">{COPY.averageHint}</span></div>
            </details>
          </div></>
        ) : (
          <div>
            <div className="field" style={{ marginTop: 12 }}><label htmlFor="csv">CSV file (up to 2 MB)</label>
              <input id="csv" type="file" accept=".csv,text/csv" onChange={(e) => onFile(e.target.files?.[0])} /></div>
            {f.columns.length > 0 && (<>
              <div className="convention">
                <div className="field"><label htmlFor="convention">How are amounts signed?</label>
                  <select id="convention" value={f.convention}
                    onChange={(e) => {
                      set({ convention: e.target.value, convNote: "", parsed: null });
                      if (e.target.value && error?.fields.includes("sign_convention")) setError(null);
                    }}
                    aria-invalid={invalid("sign_convention")} aria-describedby="conv-help">
                    <option value="">{COPY.signingPrompt}</option>
                    {CONVENTIONS.map(([v, t]) => <option key={v} value={v}>{t}</option>)}</select></div>
                <p id="conv-help" className="small muted conv-help">
                  {[f.convNote, f.convention ? COPY.signingOptionHelp[f.convention] : COPY.signingHelp,
                    invalid("sign_convention") && !f.convention ? COPY.chooseSigningField : ""].filter(Boolean).join(" ")}</p>
              </div>
              <div className="mapping-grid" role="group" aria-label="Choose columns">
                {cols.map((k) => (
                  <div className="field" key={k}><label htmlFor={`map-${k}`}>{COL_LABEL[k]}</label>
                    <select id={`map-${k}`} value={f.mapping[k] ?? ""} aria-invalid={invalid(`mapping.${k}`)}
                      onChange={(e) => set({ mapping: { ...f.mapping, [k]: e.target.value || null }, parsed: null })}>
                      <option value="">(none)</option>
                      {f.columns.map((c) => <option key={c} value={c} title={c}>{c.length > 48 ? `${c.slice(0, 47)}…` : c}</option>)}
                    </select></div>))}
              </div></>)}
            {f.columns.length > 0 && <p className="check-row"><button type="button" className="btn" onClick={checkFile} disabled={busy}>Check this file</button></p>}
            {f.parsed && (
              <div className="success" role="status">
                <p style={{ margin: 0 }}>{count(f.parsed.summary.usable)} of {count(f.parsed.summary.rows)} rows can be used.
                  {" "}{COPY.checkCredits(count(f.parsed.summary.credits))}
                  {" "}Not purchases (payments, transfers or fees), so no round-ups: {count(f.parsed.summary.non_purchases)}.
                  {f.parsed.summary.not_posted > 0 && ` ${COPY.checkNotPosted(count(f.parsed.summary.not_posted))}`}
                  {f.parsed.summary.rows > 0 && ` ${COPY.checkPurchases(count(f.parsed.summary.purchases))}`}
                  {f.parsed.summary.whole_dollar > 0 && ` ${COPY.checkWholeDollar(count(f.parsed.summary.whole_dollar))}`}
                  {Object.entries(f.parsed.summary.problems).filter(([, n]) => n > 0).map(([k, n]) =>
                    ` ${k === "invalid_amount" ? "Rows with an amount we can’t read" : k === "invalid_date" ? "Rows with a date we can’t read" : "Rows with a zero amount"}: ${count(n)}.`)}
                  {f.parsed.summary.possible_duplicates > 0 && ` Possible duplicates (kept): ${count(f.parsed.summary.possible_duplicates)}.`}</p>
                {f.parsed.summary.rows === 0 && <p style={{ margin: "8px 0 0" }}><strong>{COPY.checkNoRows}</strong></p>}
                {f.parsed.summary.rows > 0 && f.parsed.summary.purchases === 0 && <p style={{ margin: "8px 0 0" }}><strong>{COPY.checkNoPurchases}</strong></p>}
                {f.parsed.summary.unrecognised_status > 0 && (<p style={{ margin: "8px 0 0" }}><strong>{COPY.checkUnrecognised(count(f.parsed.summary.unrecognised_status))}</strong>
                  <label className="switch" style={{ marginTop: 8 }}><input type="checkbox" checked={f.countUnrecognised}
                    onChange={(e) => set({ countUnrecognised: e.target.checked })} /><span>{COPY.countUnrecognised}</span></label>
                  {f.countUnrecognised && <span className="small">{COPY.willCountUnrecognised(count(f.parsed.summary.unrecognised_status))}</span>}</p>)}
                {f.parsed.summary.ragged_rows > 0 && <p style={{ margin: "8px 0 0" }}><strong>{COPY.checkRagged(count(f.parsed.summary.ragged_rows))}</strong></p>}
                {f.parsed.summary.problems.invalid_date > 0 && <p style={{ margin: "8px 0 0" }}>{COPY.dateFormats}</p>}
                {first && <p style={{ margin: "8px 0 0" }}>{COPY.fileDates(longDate(first), longDate(last))}
                  {outside && <> <strong>{COPY.outsideDates}</strong></>}</p>}
                {f.slashDates && <p style={{ margin: "8px 0 0" }}>{COPY.slashDates}</p>}
                {outside && overlaps && <p style={{ margin: "8px 0 0" }}>
                  <button type="button" className="btn" onClick={applyFileDates}>{COPY.useFileDates}</button></p>}
              </div>)}
          </div>
        )}
      </fieldset>

      <fieldset className="step-card" id="step-2" data-step="2"><legend><span className="step-icon"><Icon name="layers" /></span><span className="step-title"><span className="step">Step 2 of 4</span>Market scenario</span></legend>
        <p className="muted small">Every scenario is made up by a published model, so you can see how round-ups behave in
          different kinds of made-up markets. <strong>{COPY.label}</strong></p>
        <div className="options">
          {!scen && !error && [0, 1, 2, 3].map((i) => (
            <div className="option choice scenario skeleton-card" key={i} role="presentation"><Skeleton height={20} width="55%" /><Skeleton height={36} /><Skeleton height={14} /><Skeleton height={14} width="80%" /></div>))}
          {(scen?.scenarios ?? []).map((s) => {
            const shape = s.styles.find((x) => x.style === f.style)?.shape;
            return (
              <label className="option choice scenario" key={s.id} data-scenario={s.id}><input type="radio" name="scenario" value={s.id}
                checked={f.scenarioId === s.id} onChange={() => set({ scenarioId: s.id })} />
                <span className="title">{s.name}<span className={`chip chip-${s.id}`}>{COPY.scenarioChip[s.id] ?? "Made-up"}</span></span>
                {shape && <Sparkline shape={shape} />}
                <span className="desc">{s.description}</span></label>);
          })}
        </div>
        <p id="style-h" className="subhead">Style</p>
        <div className="options" role="radiogroup" aria-labelledby="style-h">
          <label className="option choice"><input type="radio" name="style" value="broad" checked={f.style === "broad"}
            onChange={() => set({ style: "broad" })} /><span className="title">Broad-market style</span>
            <span className="desc">In this model: smaller dividends, slightly higher price drift.</span></label>
          <label className="option choice"><input type="radio" name="style" value="dividend" checked={f.style === "dividend"}
            onChange={() => set({ style: "dividend" })} /><span className="title">Dividend style</span>
            <span className="desc">In this model: larger dividends, slightly lower price drift.</span></label>
        </div>
      </fieldset>

      <fieldset className="step-card" id="step-3" data-step="3"><legend><span className="step-icon"><Icon name="sliders" /></span><span className="step-title"><span className="step">Step 3 of 4</span>How round-ups are invested</span></legend>
        <p className="muted small">All four are equally valid to explore. Comparing them is the point.</p>
        <div className="options">
          {STRATEGIES.map(([v, t, d]) => (
            <label className="option choice" key={v}><input type="radio" name="strategy" value={v} checked={f.strategy === v}
              onChange={() => set({ strategy: v })} /><span className="choice-icon"><Icon name={STRATEGY_ICON[v]} /></span><span className="title">{t}{v === "threshold" && <> <span className="tag">Starting setting</span></>}</span>
              <span className="desc">{d}</span></label>))}
        </div>
        <label className="switch"><input type="checkbox" checked={f.reinvest} onChange={(e) => set({ reinvest: e.target.checked })} />
          <span><span style={{ fontWeight: 650 }}>Reinvest dividends</span><br />
            <span className="small muted">Use dividend cash to buy more of the same scenario&rsquo;s shares on the day it is paid. Turn off to keep it as cash.</span></span></label>
      </fieldset>

      <fieldset className="step-card" id="step-4" data-step="4"><legend><span className="step-icon"><Icon name="calendar" /></span><span className="step-title"><span className="step">Step 4 of 4</span>Dates</span></legend>
        <p className="muted small">{range ? `This scenario runs from ${longDate(range.start)} to ${longDate(range.end)}. ` : ""}{COPY.datesNote}</p>
        <div className="fields">
          <div className="field"><label htmlFor="start">Start date</label>
            <input id="start" type="date" value={f.start} min={range?.start} max={range?.end} aria-invalid={invalid("start")}
              onChange={(e) => set({ start: e.target.value })} /></div>
          <div className="field"><label htmlFor="end">End date</label>
            <input id="end" type="date" value={f.end} min={range?.start} max={range?.end} aria-invalid={invalid("end")}
              onChange={(e) => set({ end: e.target.value })} /></div>
        </div>
      </fieldset>

      <div className="btn-row"><button className="btn btn-primary" type="submit" disabled={busy || coolingDown}>{busy ? "Running…" : "Run simulation"}</button>
        <span className="small muted">Nothing is saved unless you sign in and choose Save.</span></div>
    </form>
  );
}
