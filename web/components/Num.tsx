"use client";
// A money figure drawn as rolling digits. The text is the engine's own string, character for character: nothing is calculated here.
// Each digit sits in a one-character window; a CSS animation rolls its strip (0 to 9) up to the digit it shows. The real text is in the
// page for screen readers and search, and the animated copy is hidden from them. Under reduced motion the digits simply appear.
export function Num({ text, className = "" }: { text: string; className?: string }) {
  return (
    <span className={`num ${className}`}>
      <span className="visually-hidden">{text}</span>
      <span className="num-visual decor" aria-hidden="true">
        {[...text].map((c, i) => /[0-9]/.test(c)
          ? <span key={i} className="roll" style={{ ["--d" as string]: c, ["--i" as string]: i }} />
          : <span key={i} className="sym" data-c={c} />)}
      </span>
    </span>
  );
}
