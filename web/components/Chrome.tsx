"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { COPY } from "@/lib/copy";
import { useAuth } from "./AuthContext";
import { Icon } from "./Icon";
import { ThemeToggle } from "./ThemeToggle";

const NAV = [["/", "New simulation"], ["/compare", "Compare"], ["/saved", "Saved scenarios"], ["/how", "How this works"]];

function BrandMark() {
  return (
    <svg className="brand-mark decor" width="32" height="32" viewBox="0 0 32 32" aria-hidden="true" focusable="false">
      <defs><linearGradient id="brand-g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#4338CA" /><stop offset="1" stopColor="#14B8A6" /></linearGradient></defs>
      <rect width="32" height="32" rx="9" fill="url(#brand-g)" />
      <circle cx="16" cy="16" r="7.5" fill="none" stroke="#fff" strokeWidth="2.2" /><path d="M16 12.5v7M12.5 16h7" stroke="#fff" strokeWidth="2.2" strokeLinecap="round" />
    </svg>
  );
}

export function SiteHeader() {
  const path = usePathname();
  const { session, mode, signOut } = useAuth();
  return (
    <header className="site-header">
      <div className="bar">
        <Link className="brand" href="/"><BrandMark /><span>RoundUp</span></Link>
        <nav aria-label="Main">
          {NAV.map(([href, label]) => (
            <Link key={href} href={href} aria-current={path === href ? "page" : undefined}>{label}</Link>))}
          {mode !== "off" && (session
            ? <button type="button" className="linklike" onClick={signOut}>Sign out</button>
            : <Link href="/saved" aria-current={undefined}>Sign in</Link>)}
        </nav>
        <ThemeToggle />
      </div>
      <div className="label-strip"><p><Icon name="info" size={16} /><span>{COPY.label}</span></p></div>
    </header>
  );
}

export function SiteFooter() {
  return (
    <footer><div><Icon name="shield" size={16} /><span>{COPY.footer} <Link href="/privacy">Privacy</Link> · <Link href="/how">How this works</Link></span></div></footer>
  );
}

export function Disclaimer({ sample }: { sample: boolean }) {
  return (
    <div className="notice" role="note"><Icon name="alert" /><p><strong>{COPY.disclaimerLead}</strong> {COPY.disclaimer(sample)}</p></div>
  );
}

export function ErrorNotice({ message, requestId }: { message: string; requestId?: string | null }) {
  return (
    <div className="form-error" role="alert"><Icon name="alert" /><div><p>{message}</p>
      {requestId && <p className="small muted">Reference: {requestId}</p>}</div></div>
  );
}
