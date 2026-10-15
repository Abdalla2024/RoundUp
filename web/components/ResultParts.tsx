"use client";
import { useState } from "react";
import { counted, longDate, money, signedMoney, unsignedMoney, isNegative } from "@/lib/format";
import type { Dip, Result } from "@/lib/types";
import { Icon, type IconName } from "./Icon";

export function Headline({ result, sample }: { result: Result; sample: boolean }) {
  const s = result.summary;
  return (
    <p className="headline" id="headline">
      In this made-up scenario, <strong>{money(s.contributed)}</strong> of {sample ? "sample " : ""}round-ups ends at{" "}
      <strong>{money(s.ending_value)}</strong> on {longDate(s.as_of)}: <strong>{unsignedMoney(s.gain)}</strong>{" "}
      {isNegative(s.gain) ? "less" : "more"} than was put in.
    </p>
  );
}

function Tile({ id, term, def, value, note, icon }: { id: string; term: string; def: string; value: string; note: string; icon: IconName }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="stat">
      <dt className="stat-head"><span className="stat-icon"><Icon name={icon} size={20} /></span>
        <button type="button" className="term" aria-expanded={open} aria-controls={`def-${id}`}
          onClick={() => setOpen(!open)}>{term}</button></dt>
      <dd><span className="stat-value">{value}</span><span className="stat-note">{note}</span>
        <p className="term-def" id={`def-${id}`} hidden={!open}>{def}</p></dd>
    </div>
  );
}

export function StatTiles({ result, sample }: { result: Result; sample: boolean }) {
  const s = result.summary;
  return (
    <dl className="stats" id="stats">
      <Tile id="added" icon="coins" term="Round-ups added" value={money(s.contributed)}
        note={`from ${counted(result.transactions_used, sample ? "sample purchase" : "purchase", sample ? "sample purchases" : "purchases")}`}
        def="The spare change set aside from the purchases. This is money going in, not growth." />
      <Tile id="end" icon="wallet" term="Value at end" value={money(s.ending_value)} note={`on ${longDate(s.as_of)}`}
        def="What the shares, cash waiting to be invested and dividends kept as cash would be worth on the last day." />
      <Tile id="div" icon="percent" term="Dividends (simulated)" value={money(s.dividends_earned)}
        note={`${counted(s.dividend_buys, "payment", "payments")} reinvested`}
        def="Cash the made-up fund paid out from what its holdings earned." />
      <Tile id="growth" icon="trend" term="Growth on round-ups" value={signedMoney(s.gain)}
        note={s.gain_pct === "n/a" ? "no round-ups were added" : "compared with the round-ups added"}
        def="How far the value at the end is above, or below, the round-ups added. It can be negative." />
    </dl>
  );
}

const PART_LABEL: Record<string, string> = {
  shares: "Invested in shares", roundups_waiting: "Round-ups waiting to be invested", dividends_as_cash: "Dividends kept as cash",
  receivables: "Dividends not yet paid",
};

/** What the end value is made of (R-13.4). The widths are the engine's own basis-point shares, used as flex weights: no arithmetic here. */
export function CompositionStrip({ result }: { result: Result }) {
  const parts = result.summary.composition;
  if (!parts || parts.every((p) => p.share_bp === 0)) return null;
  const summary = parts.map((p) => `${PART_LABEL[p.key]} ${money(p.amount)}`).join(", ");
  return (
    <figure className="strip" data-testid="composition">
      <figcaption><strong>What the end value is made of</strong></figcaption>
      <div className="strip-bar" role="img" aria-label={`What the end value is made of: ${summary}.`}>
        {parts.filter((p) => p.share_bp > 0).map((p) => <span key={p.key} className={`seg seg-${p.key}`} style={{ flexGrow: p.share_bp }} />)}
      </div>
      <ul className="strip-legend">
        {parts.map((p) => <li key={p.key}><span className={`swatch seg-${p.key}`} aria-hidden="true" />{PART_LABEL[p.key]} <strong>{money(p.amount)}</strong></li>)}
      </ul>
    </figure>
  );
}

export function dipText(d: Dip | null): string {
  return d ? `on ${longDate(d.date)} the value was ${money(d.value)}, which was ${money(d.below_by)} below the ` +
             `${money(d.added)} of round-ups added by then.`
           : "the value never fell below the round-ups added in this scenario.";
}

export function DipSentence({ dip, who }: { dip: Dip | null; who?: string }) {
  return <p className="dip"><strong>{who ? `${who}, lowest` : "Lowest"} point compared with money put in:</strong> {dipText(dip)}</p>;
}

export function CashSentence({ result }: { result: Result }) {
  const s = result.summary;
  return (
    <p className="muted">On the last day, {money(s.roundups_waiting)} of round-ups was waiting to be invested and{" "}
      {money(s.dividends_as_cash)} of dividends was kept as cash. Money was invested {counted(s.roundup_buys, "time", "times")} from
      round-ups and {counted(s.dividend_buys, "time", "times")} from dividends.</p>
  );
}
