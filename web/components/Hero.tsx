import Link from "next/link";
import { Icon } from "./Icon";

/** The setup page's header: one promise, one call to action. Wording is in COPY.md ("Redesign"). */
export function Hero() {
  return (
    <section className="hero" aria-labelledby="hero-h">
      <div className="hero-text">
        <p className="eyebrow"><Icon name="spark" size={16} /> An educational demo</p>
        <h1 id="hero-h">See how spare change behaves in a made-up market</h1>
        <p className="hero-lead">Say how many purchases you make in a typical week, pick a made-up market, and watch the round-ups add up.
          Everything here is an estimate on made-up prices: no real money, no real funds, no advice.</p>
        <div className="hero-actions">
          <a className="btn btn-hero" href="#step-1">Start a simulation <Icon name="arrow" size={18} /></a>
          <Link className="btn btn-ghost" href="/how">How this works</Link>
        </div>
      </div>
    </section>
  );
}
