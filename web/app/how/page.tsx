import type { Metadata } from "next";
import { KeyPoints } from "@/components/KeyPoints";

export const metadata: Metadata = { title: "How this works" };
export default function How() {
  return (<>
    <h1>How this works</h1>
    <p>RoundUp rounds each sample or uploaded purchase up to the next dollar and invests the spare change in a made-up
      market scenario, using published rules. Every number is calculated by the RoundUp engine; this site only displays it.</p>
    <p>The scenarios come from a published, seeded model, so the same settings always give the same numbers.
      They are not real funds or real prices, and they are not forecasts.</p>
    <KeyPoints headingId="how-key-points" />
  </>);
}
