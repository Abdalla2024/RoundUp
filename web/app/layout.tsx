import type { Metadata } from "next";
import { Inter } from "next/font/google";
import type { ReactNode } from "react";
import { AuthProvider } from "@/components/AuthContext";
import { SiteFooter, SiteHeader } from "@/components/Chrome";
import { RunProvider } from "@/components/RunContext";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], display: "swap" });

export const metadata: Metadata = {
  title: { default: "RoundUp", template: "%s · RoundUp" },
  description: "An educational demo of round-up investing on made-up market scenarios. Not advice and not a forecast.",
  robots: { index: false, follow: false },          // invite-only demo
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className={inter.className}>
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
