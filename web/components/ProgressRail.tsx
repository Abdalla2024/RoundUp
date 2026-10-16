"use client";
import { useEffect, useState } from "react";
import { INPAGE_EVENT } from "@/lib/inpage";
import { Icon } from "./Icon";

const STEPS = ["Your purchases", "Market scenario", "How round-ups are invested", "Dates"];

/** A sticky progress indicator for the four setup steps. The page is one long form (every choice stays visible); the rail shows which step
 *  you are on (it follows the scroll), which are behind you, and links to each. */
export function ProgressRail() {
  const [current, setCurrent] = useState(1);
  useEffect(() => {
    // The current step is the last card whose top has passed a line a third of the way down the window.
    let frame = 0;
    const update = () => {
      frame = 0;
      const line = window.innerHeight * 0.35;
      let now = 1;
      document.querySelectorAll<HTMLElement>("[data-step]").forEach((el) => {
        if (el.getBoundingClientRect().top <= line) now = Number.parseInt(el.dataset.step ?? "1", 10);
      });
      setCurrent(now);
    };
    // Choosing a step (click or Enter) highlights it at once, and the highlight stays while the page scrolls there smoothly.
    let lockedUntil = 0;
    const onGoto = (e: Event) => {
      const id = (e as CustomEvent<{ id: string }>).detail.id;
      if (!id.startsWith("step-")) return;
      setCurrent(Number.parseInt(id.slice(5), 10) || 1);
      lockedUntil = Date.now() + 1300;
    };
    const guarded = () => { if (Date.now() >= lockedUntil) update(); else frame = 0; };
    const onScroll = () => { if (!frame) frame = requestAnimationFrame(guarded); };
    window.addEventListener(INPAGE_EVENT, onGoto);
    update();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    return () => { window.removeEventListener("scroll", onScroll); window.removeEventListener("resize", onScroll); window.removeEventListener(INPAGE_EVENT, onGoto); if (frame) cancelAnimationFrame(frame); };
  }, []);
  return (
    <nav className="rail-wrap" aria-label="Progress">
      <ol className="rail" data-current={current}>
        {STEPS.map((label, i) => {
          const n = i + 1, state = n < current ? "done" : n === current ? "current" : "todo";
          return (
            <li key={label} data-state={state}>
              <a href={`#step-${n}`} aria-current={state === "current" ? "step" : undefined}>
                <span className="rail-dot">{state === "done" ? <Icon name="check" size={14} /> : n}</span>
                <span className="rail-label"><span className="visually-hidden">Step {n} of 4: </span>{label}</span>
              </a>
            </li>);
        })}
      </ol>
    </nav>
  );
}
