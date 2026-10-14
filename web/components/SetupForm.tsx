"use client";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { COPY } from "@/lib/copy";
import { csvHeader } from "@/lib/csvHeader";
import { count, longDate } from "@/lib/format";
import type { Mapping, ParseResponse, ScenariosResponse, SimulateRequest, Strategy, Style, TransactionIn } from "@/lib/types";
import { ErrorNotice } from "./Chrome";
import { useRun, type SetupDraft } from "./RunContext";
import { useRateLimitWait } from "./useRateLimitWait";

const MAX_CSV_CHARS = 2_000_000;
const MAX_SEED = "2147483647";                   // the API's limit; compared as text, never computed
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

const DEFAULTS: SetupDraft = { source: "generate", seed: "42", perDay: "2", scenarioId: "crash-and-recovery",
  style: "broad", strategy: "threshold", reinvest: true, start: "2015-01-02", end: "2024-12-31", csv: null,
  columns: [], mapping: {}, convention: "", convNote: "", parsed: null, slashDates: false };

/** Which column pickers a sign option needs (reviewer M4). */
function visibleColumns(convention: string, mapping: Mapping): Col[] {
  if (convention === "separate_columns") return ["date", "debit", "credit", "status", "description"];
  if (convention === "type_column") return ["date", "amount", "type", "status", "description"];
  if (convention) return ["date", "amount", "status", "description"];
  return ["date", "amount", ...(["debit", "credit", "type"] as Col[]).filter((k) => mapping[k]), "status", "description"];
}
const validSeed = (s: string) => /^\d{1,10}$/.test(s) && (s.length < 10 || s <= MAX_SEED);

export function SetupForm() {
  const router = useRouter();
  const { setRun, draft, setDraft } = useRun();
  const [f, setF] = useState<SetupDraft>(draft ?? DEFAULTS);       // reviewer M1: settings survive leaving the page
  const set = (patch: Partial<SetupDraft>) => setF((cur) => ({ ...cur, ...patch }));
  useEffect(() => { setDraft(f); }, [f, setDraft]);
  const [scen, setScen] = useState<ScenariosResponse | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [busy, setBusy] = useState(false);
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
    if (f.source === "generate") {
      if (!validSeed(f.seed)) { setError(new ApiError(422, "INVALID_INPUT", COPY.seedError, ["generate.seed"])); return; }
      if (!/^[123]$/.test(f.perDay)) { setError(new ApiError(422, "INVALID_INPUT", COPY.perDayError, ["generate.max_per_day"])); return; }
      req = { ...req, generate: { seed: Number.parseInt(f.seed, 10), max_per_day: Number.parseInt(f.perDay, 10) } };
    } else {
      if (!f.parsed) { setError(new ApiError(422, "INVALID_INPUT", "Upload a CSV file and check it first.")); return; }
      const txs: TransactionIn[] = f.parsed.transactions.filter((t) => t.problem === null && t.posted_date && t.amount)
        .map((t) => ({ posted_date: t.posted_date!, amount: t.amount!, direction: t.direction, status: t.status, category: t.category }));
      if (txs.length === 0) { setError(new ApiError(422, "INVALID_INPUT", "No usable rows were found in this file.")); return; }
      req = { ...req, transactions: txs };
    }
    setBusy(true);
    try {
      const response = await api.simulate(req);
      setRun({ request: req, response, sample: f.source === "generate" });
      router.push("/results");
    } catch (e) { noteRateLimit(e as ApiError); setError(e as ApiError); } finally { setBusy(false); }
  }

  return (
    <form onSubmit={onSubmit} noValidate aria-describedby={error ? "form-error" : undefined}>
      {error && <div ref={errorRef} tabIndex={-1} id="form-error"><ErrorNotice message={error.message} requestId={error.requestId} /></div>}

      <fieldset><legend><span className="step">Step 1 of 4</span>Your purchases</legend>
        <p className="muted small">Round-ups come from purchases. Use sample spending, or upload a CSV export from your bank.
          Uploaded files are read in your session and not stored.</p>
        <div className="options">
          <label className="option"><input type="radio" name="source" value="generate" checked={f.source === "generate"}
            onChange={() => set({ source: "generate" })} /><span className="title">Generate sample spending</span>
            <span className="desc">Made-up everyday purchases, the same every time for the same number.</span></label>
          <label className="option"><input type="radio" name="source" value="upload" checked={f.source === "upload"}
            onChange={() => set({ source: "upload" })} /><span className="title">Upload a CSV</span>
            <span className="desc">You choose which columns hold the date and amount. Merchant names are never stored.</span></label>
        </div>
        {f.source === "generate" ? (
          <div className="fields">
            <div className="field"><label htmlFor="seed">Sample number (same number, same purchases)</label>
              <input id="seed" inputMode="numeric" value={f.seed} onChange={(e) => set({ seed: e.target.value })}
                aria-invalid={invalid("generate.seed")} aria-describedby="seed-help" />
              <span id="seed-help" className="small muted">{COPY.seedHint}</span></div>
            <div className="field"><label htmlFor="perday">Purchases per day, at most</label>
              <input id="perday" inputMode="numeric" value={f.perDay} onChange={(e) => set({ perDay: e.target.value })}
                aria-invalid={invalid("generate.max_per_day")} aria-describedby="perday-help" />
              <span id="perday-help" className="small muted">1, 2 or 3.</span></div>
          </div>
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

      <fieldset><legend><span className="step">Step 2 of 4</span>Market scenario</legend>
        <p className="muted small">Every scenario is made up by a published model, so you can see how round-ups behave in
          different kinds of made-up markets. <strong>{COPY.label}</strong></p>
        <div className="options">
          {(scen?.scenarios ?? []).map((s) => (
            <label className="option" key={s.id}><input type="radio" name="scenario" value={s.id}
              checked={f.scenarioId === s.id} onChange={() => set({ scenarioId: s.id })} />
              <span className="title">{s.name}</span><span className="desc">{s.description}</span></label>))}
        </div>
        <p id="style-h" style={{ margin: "20px 0 0", fontWeight: 650 }}>Style</p>
        <div className="options" role="radiogroup" aria-labelledby="style-h">
          <label className="option"><input type="radio" name="style" value="broad" checked={f.style === "broad"}
            onChange={() => set({ style: "broad" })} /><span className="title">Broad-market style</span>
            <span className="desc">In this model: smaller dividends, slightly higher price drift.</span></label>
          <label className="option"><input type="radio" name="style" value="dividend" checked={f.style === "dividend"}
            onChange={() => set({ style: "dividend" })} /><span className="title">Dividend style</span>
            <span className="desc">In this model: larger dividends, slightly lower price drift.</span></label>
        </div>
      </fieldset>

      <fieldset><legend><span className="step">Step 3 of 4</span>How round-ups are invested</legend>
        <p className="muted small">All four are equally valid to explore. Comparing them is the point.</p>
        <div className="options">
          {STRATEGIES.map(([v, t, d]) => (
            <label className="option" key={v}><input type="radio" name="strategy" value={v} checked={f.strategy === v}
              onChange={() => set({ strategy: v })} /><span className="title">{t}{v === "threshold" && <> <span className="tag">Starting setting</span></>}</span>
              <span className="desc">{d}</span></label>))}
        </div>
        <label className="switch"><input type="checkbox" checked={f.reinvest} onChange={(e) => set({ reinvest: e.target.checked })} />
          <span><span style={{ fontWeight: 650 }}>Reinvest dividends</span><br />
            <span className="small muted">Use dividend cash to buy more of the same scenario&rsquo;s shares on the day it is paid. Turn off to keep it as cash.</span></span></label>
      </fieldset>

      <fieldset><legend><span className="step">Step 4 of 4</span>Dates</legend>
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
