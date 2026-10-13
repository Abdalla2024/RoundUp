"use client";
// Magic-link return. supabase-js (flowType "pkce", detectSessionInUrl) exchanges the code in the URL for a session
// when the client starts; we then go to the saved list.
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { auth } from "@/lib/auth";

export default function AuthCallback() {
  const router = useRouter();
  const [msg, setMsg] = useState("Signing you in…");
  useEffect(() => {
    let tries = 0;
    const t = setInterval(async () => {
      tries += 1;
      if (await auth.current()) { clearInterval(t); router.replace("/saved"); }
      else if (tries > 20) { clearInterval(t); setMsg("That sign-in link didn’t work or has expired. Request a new one from Saved scenarios."); }
    }, 250);
    return () => clearInterval(t);
  }, [router]);
  return (<><h1>Sign in</h1><p role="status">{msg}</p></>);
}
