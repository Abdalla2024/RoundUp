"use client";
import { useState } from "react";
import { counted, longDate, money, signedMoney, unsignedMoney, isNegative } from "@/lib/format";
import type { Dip, Result } from "@/lib/types";

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

function Tile({ id, term, def, value, note }: { id: string; term: string; def: string; value: string; note: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="stat">
      <dt><button type="button" className="term" aria-expanded={open} aria-controls={`def-${id}`}
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
      <Tile id="added" term="Round-ups added" value={money(s.contributed)}
        note={`from ${counted(result.transactions_used, sample ? "sample purchase" : "purchase", sample ? "sample purchases" : "purchases")}`}
        def="The spare change set aside from the purchases. This is money going in, not growth." />
      <Tile id="end" term="Value at end" value={money(s.ending_value)} note={`on ${longDate(s.as_of)}`}
        def="What the shares, cash waiting to be invested and dividends kept as cash would be worth on the last day." />
      <Tile id="div" term="Dividends (simulated)" value={money(s.dividends_earned)}
        note={`${counted(s.dividend_buys, "payment", "payments")} reinvested`}
        def="Cash the made-up fund paid out from what its holdings earned." />
      <Tile id="growth" term="Growth on round-ups" value={signedMoney(s.gain)}
        note={s.gain_pct === "n/a" ? "no round-ups were added" : "compared with the round-ups added"}
        def="How far the value at the end is above, or below, the round-ups added. It can be negative." />
    </dl>
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
