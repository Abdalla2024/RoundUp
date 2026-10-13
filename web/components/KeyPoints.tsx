"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { COPY } from "@/lib/copy";
import type { AssumptionsResponse } from "@/lib/types";

/** Key points always visible; the full assumptions and the rule codes are collapsed (owner decision). */
export function KeyPoints({ headingId = "key-points-h" }: { headingId?: string }) {
  const [data, setData] = useState<AssumptionsResponse | null>(null);
  useEffect(() => { api.assumptions().then(setData).catch(() => setData(null)); }, []);
  return (
    <section className="assumptions panel" aria-labelledby={headingId}>
      <h2 id={headingId}>Key points</h2>
      <ul className="key-points">
        {COPY.keyPoints.map(([k, t]) => <li key={k}><strong>{k}</strong> {t}</li>)}
      </ul>
      {data && (
        <details className="all-assumptions">
          <summary>All assumptions ({data.assumptions.length})</summary>
          <dl>{data.assumptions.map((a) => [<dt key={a.id + "t"}>{a.title}</dt>, <dd key={a.id + "d"}>{a.text}</dd>])}</dl>
          <p className="small muted" style={{ marginTop: 12 }}>{data.disclaimer}</p>
          <details className="refs"><summary>Rule references</summary>
            <ul className="small">{data.assumptions.map((a) => <li key={a.id}>{a.title}: {a.id}</li>)}</ul>
          </details>
        </details>
      )}
    </section>
  );
}
