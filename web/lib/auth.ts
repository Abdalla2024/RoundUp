"use client";
// Sign-in adapter. "supabase": magic link via @supabase/supabase-js (PKCE). "standin": LOCAL TESTS ONLY, a token
// from tools/standin (next.config.ts refuses to build it on Vercel). "off": no sign-in configured.
import { createClient, type SupabaseClient } from "@supabase/supabase-js";

export const SUPABASE_URL = (process.env.NEXT_PUBLIC_SUPABASE_URL || "").replace(/\/$/, "");
export const PUBLISHABLE_KEY = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY || "";
export type AuthMode = "supabase" | "standin" | "off";
export const AUTH_MODE: AuthMode = process.env.NEXT_PUBLIC_AUTH_MODE === "standin" ? "standin"
  : SUPABASE_URL && PUBLISHABLE_KEY ? "supabase" : "off";

export interface Session { token: string; email: string }
type Listener = (s: Session | null) => void;

let client: SupabaseClient | null = null;
function supabase(): SupabaseClient {
  if (!client) {
    client = createClient(SUPABASE_URL, PUBLISHABLE_KEY, {
      auth: { flowType: "pkce", persistSession: true, autoRefreshToken: true, detectSessionInUrl: true },
    });
  }
  return client;
}

let standinSession: Session | null = null;     // memory only: tests sign in fresh each time
const listeners = new Set<Listener>();
const emit = (s: Session | null) => listeners.forEach((l) => l(s));

export const auth = {
  mode: AUTH_MODE,
  async current(): Promise<Session | null> {
    if (AUTH_MODE === "standin") return standinSession;
    if (AUTH_MODE === "off") return null;
    const { data } = await supabase().auth.getSession();     // browser only: the API verifies the token itself
    const s = data.session;
    return s ? { token: s.access_token, email: s.user.email ?? "" } : null;
  },
  /** Sends a magic link (supabase) or signs in immediately (standin). Returns true when already signed in. */
  async signIn(email: string): Promise<boolean> {
    if (AUTH_MODE === "standin") {
      const r = await fetch(`${SUPABASE_URL}/standin/token`, { method: "POST", body: JSON.stringify({ email }),
        headers: { "Content-Type": "application/json" } });
      if (!r.ok) throw new Error("Sign-in failed.");
      const j = (await r.json()) as { access_token: string };
      standinSession = { token: j.access_token, email };
      emit(standinSession);
      return true;
    }
    if (AUTH_MODE === "off") throw new Error("Sign-in is not set up.");
    const { error } = await supabase().auth.signInWithOtp({
      email, options: { emailRedirectTo: `${window.location.origin}/auth/callback`, shouldCreateUser: false },
    });
    if (error) throw new Error("We couldn’t send a sign-in link to that address. Check it and try again.");
    return false;
  },
  async signOut(): Promise<void> {
    if (AUTH_MODE === "standin") { standinSession = null; emit(null); return; }
    if (AUTH_MODE === "supabase") await supabase().auth.signOut();
    emit(null);
  },
  onChange(l: Listener): () => void {
    listeners.add(l);
    let unsub = () => {};
    if (AUTH_MODE === "supabase") {
      const { data } = supabase().auth.onAuthStateChange((_e, s) =>
        l(s ? { token: s.access_token, email: s.user.email ?? "" } : null));
      unsub = () => data.subscription.unsubscribe();
    }
    return () => { listeners.delete(l); unsub(); };
  },
};
