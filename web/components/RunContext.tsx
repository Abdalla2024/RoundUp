"use client";
import { createContext, useContext, useState, type ReactNode } from "react";
import type { CompareRequest, CompareResponse, Mapping, ParseResponse, SimulateRequest, SimulateResponse, Strategy,
  Style } from "@/lib/types";

// The last run, and the setup form as last filled in, live in memory only (nothing is stored in the browser).
export interface LastRun { request: SimulateRequest; response: SimulateResponse; sample: boolean; savedName?: string }
export interface SetupDraft {
  source: "generate" | "upload"; seed: string; perDay: string; scenarioId: string; style: Style; strategy: Strategy;
  reinvest: boolean; start: string; end: string; csv: string | null; columns: string[]; mapping: Mapping;
  convention: string; parsed: ParseResponse | null; slashDates: boolean;
}
interface Ctx {
  run: LastRun | null; setRun: (r: LastRun | null) => void;
  compare: { request: CompareRequest; response: CompareResponse; sample: boolean } | null;
  setCompare: (c: Ctx["compare"]) => void;
  draft: SetupDraft | null; setDraft: (d: SetupDraft) => void;
}
const RunCtx = createContext<Ctx | null>(null);

export function RunProvider({ children, initial }: { children: ReactNode; initial?: Partial<Ctx> }) {
  const [run, setRun] = useState<LastRun | null>(initial?.run ?? null);
  const [compare, setCompare] = useState<Ctx["compare"]>(initial?.compare ?? null);
  const [draft, setDraft] = useState<SetupDraft | null>(initial?.draft ?? null);
  return <RunCtx.Provider value={{ run, setRun, compare, setCompare, draft, setDraft }}>{children}</RunCtx.Provider>;
}
export function useRun(): Ctx {
  const c = useContext(RunCtx);
  if (!c) throw new Error("useRun outside RunProvider");
  return c;
}
