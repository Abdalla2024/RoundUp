"use client";
import { createContext, useContext, useState, type ReactNode } from "react";
import type { CompareRequest, CompareResponse, SimulateRequest, SimulateResponse } from "@/lib/types";

// The last run lives in memory only (nothing is stored in the browser).
export interface LastRun { request: SimulateRequest; response: SimulateResponse; sample: boolean; savedName?: string }
interface Ctx {
  run: LastRun | null; setRun: (r: LastRun | null) => void;
  compare: { request: CompareRequest; response: CompareResponse; sample: boolean } | null;
  setCompare: (c: Ctx["compare"]) => void;
}
const RunCtx = createContext<Ctx | null>(null);

export function RunProvider({ children, initial }: { children: ReactNode; initial?: Partial<Ctx> }) {
  const [run, setRun] = useState<LastRun | null>(initial?.run ?? null);
  const [compare, setCompare] = useState<Ctx["compare"]>(initial?.compare ?? null);
  return <RunCtx.Provider value={{ run, setRun, compare, setCompare }}>{children}</RunCtx.Provider>;
}
export function useRun(): Ctx {
  const c = useContext(RunCtx);
  if (!c) throw new Error("useRun outside RunProvider");
  return c;
}
