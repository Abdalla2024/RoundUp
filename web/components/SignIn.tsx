"use client";
import { useState } from "react";
import { auth } from "@/lib/auth";
import { COPY } from "@/lib/copy";
import { useAuth } from "./AuthContext";

export function SignInForm({ intro }: { intro?: string }) {
  const { mode, refresh } = useAuth();
  const [email, setEmail] = useState("");
  const [state, setState] = useState<"idle" | "sending" | "sent" | "error">("idle");
  const [error, setError] = useState("");
  if (mode === "off") return <p className="muted">{COPY.signInNotSetUp}</p>;
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) { setState("error"); setError("Enter an email address like name@example.com."); return; }
    setState("sending");
    try {
      const done = await auth.signIn(email);
      if (done) { await refresh(); setState("idle"); } else setState("sent");
    } catch (err) { setState("error"); setError((err as Error).message); }
  }
  if (state === "sent") return <p role="status" className="success">Check your email for a sign-in link. It works once.</p>;
  return (
    <form className="inline-form" onSubmit={submit} noValidate>
      {intro && <p className="muted" style={{ width: "100%" }}>{intro}</p>}
      <div className="field"><label htmlFor="email">Email</label>
        <input id="email" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)}
          aria-invalid={state === "error"} aria-describedby={state === "error" ? "email-error" : undefined} /></div>
      <button className="btn btn-primary" type="submit" disabled={state === "sending"}>Email me a sign-in link</button>
      {state === "error" && <p id="email-error" role="alert" className="form-error" style={{ width: "100%" }}>{error}</p>}
    </form>
  );
}
