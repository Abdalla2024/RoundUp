import type { Metadata } from "next";
import { Manrope } from "next/font/google";
import type { ReactNode } from "react";
import { AuthProvider } from "@/components/AuthContext";
import { SiteFooter, SiteHeader } from "@/components/Chrome";
import { RunProvider } from "@/components/RunContext";
import "./tokens.css";
import "./globals.css";

// Self-hosted: next/font downloads the font at build time and serves it from this site, so no request goes to a font server when someone visits.
const font = Manrope({ subsets: ["latin"], display: "swap", variable: "--font" });

// Applies a remembered light/dark choice before the page paints (no flash). Without a choice the system setting decides (tokens.css).
const THEME_SCRIPT = "try{var t=localStorage.getItem('roundup-theme');if(t==='light'||t==='dark')document.documentElement.setAttribute('data-theme',t)}catch(e){}";

export const metadata: Metadata = {
  title: { default: "RoundUp", template: "%s · RoundUp" },
  description: "An educational demo of round-up investing on made-up market scenarios. Not advice and not a forecast.",
  robots: { index: false, follow: false },          // invite-only demo
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className={font.variable} suppressHydrationWarning>
      <head><script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} /></head>
      <body>
        <a className="skip" href="#main">Skip to main content</a>
        <AuthProvider><RunProvider>
          <SiteHeader />
          <main id="main" tabIndex={-1}>{children}</main>
          <SiteFooter />
        </RunProvider></AuthProvider>
      </body>
    </html>
  );
}
