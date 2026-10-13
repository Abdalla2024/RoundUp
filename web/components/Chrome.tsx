"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { COPY } from "@/lib/copy";
import { useAuth } from "./AuthContext";

const NAV = [["/", "New simulation"], ["/compare", "Compare"], ["/saved", "Saved scenarios"], ["/how", "How this works"]];

export function SiteHeader() {
  const path = usePathname();
  const { session, mode, signOut } = useAuth();
  return (
    <header className="topbar-wrap">
      <div className="topbar"><div className="topbar-inner">
        <Link className="logo" href="/">RoundUp</Link>
        <nav aria-label="Main">
          {NAV.map(([href, label]) => (
            <Link key={href} href={href} aria-current={path === href ? "page" : undefined}>{label}</Link>))}
          {mode !== "off" && (session
            ? <button type="button" className="linklike" onClick={signOut}>Sign out</button>
            : <Link href="/saved" aria-current={undefined}>Sign in</Link>)}
        </nav>
      </div></div>
      <div className="label-strip"><p>{COPY.label}</p></div>
    </header>
  );
}

export function SiteFooter() {
  return (
    <footer><div>{COPY.footer} <Link href="/privacy">Privacy</Link> · <Link href="/how">How this works</Link></div></footer>
  );
}

export function Disclaimer({ sample }: { sample: boolean }) {
  return (
    <div className="notice" role="note"><p><strong>{COPY.disclaimerLead}</strong> {COPY.disclaimer(sample)}</p></div>
  );
}

export function ErrorNotice({ message, requestId }: { message: string; requestId?: string | null }) {
  return (
    <div className="form-error" role="alert"><p style={{ margin: 0 }}>{message}</p>
      {requestId && <p className="small muted" style={{ margin: "4px 0 0" }}>Reference: {requestId}</p>}</div>
  );
}
