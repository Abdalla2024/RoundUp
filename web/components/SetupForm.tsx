"use client";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { COPY } from "@/lib/copy";
import { csvHeader } from "@/lib/csvHeader";
import { count, longDate } from "@/lib/format";
import type { Mapping, ParseResponse, ScenariosResponse, SimulateRequest, Strategy, Style, TransactionIn } from "@/lib/types";
import { ErrorNotice } from "./Chrome";
import { useRun } from "./RunContext";

const MAX_CSV_CHARS = 2_000_000;
const STRATEGIES: [Strategy, string, string][] = [
  ["threshold", "When they reach $5", "Saved-up round-ups are invested once they add up to $5."],
  ["next_session", "After every purchase day", "Each day’s round-ups are invested on the next trading day."],
  ["weekly", "Once a week", "The week’s round-ups are invested after Sunday."],
  ["monthly", "Once a month", "The month’s round-ups are invested after the month ends."],
];
const CONVENTIONS: [string, string][] = [
  ["debits_positive", "Purchases are positive numbers"], ["debits_negative", "Purchases are negative numbers"],
  ["separate_columns", "Separate columns for money out and money in"], ["type_column", "A column says debit or credit"],
];

export function SetupForm() {
  const router = useRouter();
  const { setRun } = useRun();
  const [scen, setScen] = useState<ScenariosResponse | null>(null);
  const [source, setSource] = useState<"generate" | "upload">("generate");
  const [seed, setSeed] = useState("42");
  const [perDay, setPerDay] = useState("2");
  const [scenarioId, setScenarioId] = useState("crash-and-recovery");
  const [style, setStyle] = useState<Style>("broad");
  const [strategy, setStrategy] = useState<Strategy>("threshold");
  const [reinvest, setReinvest] = useState(true);
  const [start, setStart] = useState("2015-01-02");
  const [end, setEnd] = useState("2024-12-31");
  const [error, setError] = useState<ApiError | null>(null);
  const [busy, setBusy] = useState(false);
  // CSV
  const [csv, setCsv] = useState<string | null>(null);
  const [columns, setColumns] = useState<string[]>([]);
  const [mapping, setMapping] = useState<Mapping>({});
  const [convention, setConvention] = useState("");
  const [parsed, setParsed] = useState<ParseResponse | null>(null);
  const [needConvention, setNeedConvention] = useState(false);
  const errorRef = useRef<HTMLDivElement>(null);

  useEffect(() => { api.scenarios().then(setScen).catch((e) => setError(e as ApiError)); }, []);
  useEffect(() => { if (error) errorRef.current?.focus(); }, [error]);

  const range = scen?.scenarios.find((s) => s.id === scenarioId)?.styles.find((s) => s.style === style);
  const invalid = (f: string) => Boolean(error?.fields.some((x) => x === f || x.startsWith(f + ".")));

  async function onFile(file: File | undefined) {
    setParsed(null); setError(null); setColumns([]); setCsv(null);
    if (!file) return;
    const text = await file.text();
    if (text.length > MAX_CSV_CHARS) {
      setError(new ApiError(413, "PAYLOAD_TOO_LARGE", "This file is too large. The limit is 2 MB or 20,000 rows."));
      return;
    }
    setCsv(text);
    const cols = csvHeader(text);
    setColumns(cols);
    const guess = (re: RegExp) => cols.find((c) => re.test(c)) ?? null;
    setMapping({ date: guess(/date/i), amount: guess(/amount/i), description: guess(/desc|merchant|name/i) });
  }

  async function checkFile() {
    if (!csv) return;
    setBusy(true); setError(null);
    try {
      const res = await api.parse(csv, mapping, convention || null);
      setParsed(res); setNeedConvention(false);
    } catch (e) {
      const err = e as ApiError;
      if (err.code === "SIGN_CONVENTION_REQUIRED") setNeedConvention(true);
      setError(err);
    } finally { setBusy(false); }
  }

  async function onSubmit(ev: React.FormEvent) {
    ev.preventDefault();
    setError(null);
    let req: SimulateRequest = { scenario_id: scenarioId, style, start, end, strategy, reinvest };
    if (source === "generate") {
      if (!/^\d{1,10}$/.test(seed) || !/^[123]$/.test(perDay)) {
        setError(new ApiError(422, "INVALID_INPUT", "Use a whole number for the sample number, and 1, 2 or 3 purchases per day.",
          ["generate.seed", "generate.max_per_day"]));
        return;
      }
      req = { ...req, generate: { seed: Number.parseInt(seed, 10), max_per_day: Number.parseInt(perDay, 10) } };
    } else {
      if (!parsed) { setError(new ApiError(422, "INVALID_INPUT", "Upload a CSV file and check it first.")); return; }
      const txs: TransactionIn[] = parsed.transactions.filter((t) => t.problem === null && t.posted_date && t.amount)
        .map((t) => ({ posted_date: t.posted_date!, amount: t.amount!, direction: t.direction, status: t.status, category: t.category }));
      if (txs.length === 0) { setError(new ApiError(422, "INVALID_INPUT", "No usable rows were found in this file.")); return; }
      req = { ...req, transactions: txs };
    }
    setBusy(true);
    try {
      const response = await api.simulate(req);
      setRun({ request: req, response, sample: source === "generate" });
      router.push("/results");
    } catch (e) { setError(e as ApiError); } finally { setBusy(false); }
  }

  return (
    <form onSubmit={onSubmit} noValidate aria-describedby={error ? "form-error" : undefined}>
      {error && <div ref={errorRef} tabIndex={-1} id="form-error"><ErrorNotice message={error.message} requestId={error.requestId} /></div>}

      <fieldset><legend><span className="step">Step 1 of 4</span>Your purchases</legend>
        <p className="muted small">Round-ups come from purchases. Use sample spending, or upload a CSV export from your bank.
          Uploaded files are read in your session and not stored.</p>
        <div className="options">
          <label className="option"><input type="radio" name="source" value="generate" checked={source === "generate"}
            onChange={() => setSource("generate")} /><span className="title">Generate sample spending</span>
            <span className="desc">Made-up everyday purchases, the same every time for the same number.</span></label>
          <label className="option"><input type="radio" name="source" value="upload" checked={source === "upload"}
            onChange={() => setSource("upload")} /><span className="title">Upload a CSV</span>
            <span className="desc">You choose which columns hold the date and amount. Merchant names are never stored.</span></label>
        </div>
        {source === "generate" ? (
          <div className="fields">
            <div className="field"><label htmlFor="seed">Sample number (same number, same purchases)</label>
              <input id="seed" inputMode="numeric" value={seed} onChange={(e) => setSeed(e.target.value)}
                aria-invalid={invalid("generate.seed")} aria-describedby="seed-help" />
              <span id="seed-help" className="small muted">Any whole number.</span></div>
            <div className="field"><label htmlFor="perday">Purchases per day, at most</label>
              <input id="perday" inputMode="numeric" value={perDay} onChange={(e) => setPerDay(e.target.value)}
                aria-invalid={invalid("generate.max_per_day")} aria-describedby="perday-help" />
              <span id="perday-help" className="small muted">1, 2 or 3.</span></div>
          </div>
        ) : (
          <div>
            <div className="field" style={{ marginTop: 12 }}><label htmlFor="csv">CSV file (up to 2 MB)</label>
              <input id="csv" type="file" accept=".csv,text/csv" onChange={(e) => onFile(e.target.files?.[0])} /></div>
            {columns.length > 0 && (
              <div className="fields" role="group" aria-label="Choose columns">
                {(["date", "amount", "description"] as const).map((k) => (
                  <div className="field" key={k}><label htmlFor={`map-${k}`}>{k === "date" ? "Date column" : k === "amount" ? "Amount column" : "Description column (optional)"}</label>
                    <select id={`map-${k}`} value={mapping[k] ?? ""} aria-invalid={invalid(`mapping.${k}`)}
                      onChange={(e) => setMapping({ ...mapping, [k]: e.target.value || null })}>
                      <option value="">(none)</option>{columns.map((c) => <option key={c} value={c}>{c}</option>)}
                    </select></div>))}
                <div className="field"><label htmlFor="convention">How are amounts signed?</label>
                  <select id="convention" value={convention} onChange={(e) => setConvention(e.target.value)}
                    aria-invalid={needConvention} aria-describedby={needConvention ? "conv-help" : undefined}>
                    <option value="">Work it out from the columns</option>
                    {CONVENTIONS.map(([v, t]) => <option key={v} value={v}>{t}</option>)}</select>
                  {needConvention && <span id="conv-help" className="small">In this file, are purchases positive or negative numbers?</span>}</div>
              </div>)}
            {columns.length > 0 && <p><button type="button" className="btn" onClick={checkFile} disabled={busy}>Check this file</button></p>}
            {parsed && (
              <div className="success" role="status">
                <p style={{ margin: 0 }}>{count(parsed.summary.usable)} of {count(parsed.summary.rows)} rows can be used.
                  {" "}{count(parsed.summary.non_purchases)} are not purchases (payments, transfers, refunds or fees) and add no round-ups.
                  {Object.entries(parsed.summary.problems).filter(([, n]) => n > 0).map(([k, n]) =>
                    ` ${count(n)} ${k === "invalid_amount" ? "have an amount we can’t read" : k === "invalid_date" ? "have a date we can’t read" : "are zero"}.`)}
                  {parsed.summary.possible_duplicates > 0 && ` ${count(parsed.summary.possible_duplicates)} look like possible duplicates (kept).`}</p>
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
              checked={scenarioId === s.id} onChange={() => setScenarioId(s.id)} />
              <span className="title">{s.name}</span><span className="desc">{s.description}</span></label>))}
        </div>
        <p id="style-h" style={{ margin: "20px 0 0", fontWeight: 650 }}>Style</p>
        <div className="options" role="radiogroup" aria-labelledby="style-h">
          <label className="option"><input type="radio" name="style" value="broad" checked={style === "broad"}
            onChange={() => setStyle("broad")} /><span className="title">Broad-market style</span>
            <span className="desc">In this model: smaller dividends, slightly higher price drift.</span></label>
          <label className="option"><input type="radio" name="style" value="dividend" checked={style === "dividend"}
            onChange={() => setStyle("dividend")} /><span className="title">Dividend style</span>
            <span className="desc">In this model: larger dividends, slightly lower price drift.</span></label>
        </div>
      </fieldset>

      <fieldset><legend><span className="step">Step 3 of 4</span>How round-ups are invested</legend>
        <p className="muted small">All four are equally valid to explore. Comparing them is the point.</p>
        <div className="options">
          {STRATEGIES.map(([v, t, d]) => (
            <label className="option" key={v}><input type="radio" name="strategy" value={v} checked={strategy === v}
              onChange={() => setStrategy(v)} /><span className="title">{t}{v === "threshold" && <> <span className="tag">Starting setting</span></>}</span>
              <span className="desc">{d}</span></label>))}
        </div>
        <label className="switch"><input type="checkbox" checked={reinvest} onChange={(e) => setReinvest(e.target.checked)} />
          <span><span style={{ fontWeight: 650 }}>Reinvest dividends</span><br />
            <span className="small muted">Use dividend cash to buy more of the same scenario&rsquo;s shares on the day it is paid. Turn off to keep it as cash.</span></span></label>
      </fieldset>

      <fieldset><legend><span className="step">Step 4 of 4</span>Dates</legend>
        <p className="muted small">{range ? `This scenario runs from ${longDate(range.start)} to ${longDate(range.end)}. ` : ""}{COPY.datesNote}</p>
        <div className="fields">
          <div className="field"><label htmlFor="start">Start date</label>
            <input id="start" type="date" value={start} min={range?.start} max={range?.end} aria-invalid={invalid("start")}
              onChange={(e) => setStart(e.target.value)} /></div>
          <div className="field"><label htmlFor="end">End date</label>
            <input id="end" type="date" value={end} min={range?.start} max={range?.end} aria-invalid={invalid("end")}
              onChange={(e) => setEnd(e.target.value)} /></div>
        </div>
      </fieldset>

      <div className="btn-row"><button className="btn btn-primary" type="submit" disabled={busy}>{busy ? "Running…" : "Run simulation"}</button>
        <span className="small muted">Nothing is saved unless you sign in and choose Save.</span></div>
    </form>
  );
}
