"use client";
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { auth, type AuthMode, type Session } from "@/lib/auth";

interface Ctx { session: Session | null; mode: AuthMode; ready: boolean; signOut: () => Promise<void>; refresh: () => Promise<void> }
const AuthCtx = createContext<Ctx | null>(null);

export function AuthProvider({ children, initial }: { children: ReactNode; initial?: { session: Session | null; mode?: AuthMode } }) {
  const [session, setSession] = useState<Session | null>(initial?.session ?? null);
  const [ready, setReady] = useState(Boolean(initial));
  const mode = initial?.mode ?? auth.mode;
  const refresh = async () => { if (!initial) setSession(await auth.current()); setReady(true); };
  useEffect(() => {
    if (initial) return;
    refresh();
    return auth.onChange(setSession);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return <AuthCtx.Provider value={{ session, mode, ready, refresh,
    signOut: async () => { await auth.signOut(); setSession(null); } }}>{children}</AuthCtx.Provider>;
}
export function useAuth(): Ctx {
  const c = useContext(AuthCtx);
  if (!c) throw new Error("useAuth outside AuthProvider");
  return c;
}
