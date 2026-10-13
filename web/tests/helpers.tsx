import { render } from "@testing-library/react";
import type { ReactNode } from "react";
import { AuthProvider } from "@/components/AuthContext";
import { RunProvider, type LastRun } from "@/components/RunContext";
import type { AuthMode, Session } from "@/lib/auth";
import type { CompareRequest, CompareResponse } from "@/lib/types";
import simulate from "./fixtures/simulate.json";
import compareFx from "./fixtures/compare.json";

export const SESSION: Session = { token: "test-token", email: "a@example.test" };
export const RUN = { request: simulate.request, response: simulate.response, sample: true } as unknown as LastRun;
export const COMPARE = { request: compareFx.request, response: compareFx.response, sample: true } as unknown as
  { request: CompareRequest; response: CompareResponse; sample: boolean };

export function renderWith(ui: ReactNode, opts: { run?: LastRun | null; session?: Session | null; mode?: AuthMode;
  compare?: typeof COMPARE | null } = {}) {
  return render(
    <AuthProvider initial={{ session: opts.session ?? null, mode: opts.mode ?? "supabase" }}>
      <RunProvider initial={{ run: opts.run ?? null, compare: opts.compare ?? null }}>{ui}</RunProvider>
    </AuthProvider>);
}

/** Every "-?d+.dd" string anywhere in an API response: the only money values the UI may show. */
export function apiMoneyStrings(obj: unknown, out = new Set<string>()): Set<string> {
  if (typeof obj === "string" && /^-?\d+\.\d{2}$/.test(obj)) out.add(obj.replace(/^-/, ""));
  else if (Array.isArray(obj)) obj.forEach((x) => apiMoneyStrings(x, out));
  else if (obj && typeof obj === "object") Object.values(obj).forEach((x) => apiMoneyStrings(x, out));
  return out;
}
/** Every dollar figure shown on screen, normalised to "1234.56". */
export function shownMoney(text: string): string[] {
  return [...text.matchAll(/\$([\d,]+\.\d{2})/g)].map((m) => m[1].replace(/,/g, ""));
}
