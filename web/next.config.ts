import type { NextConfig } from "next";
import { securityHeaders } from "./config/headers";

// Safety: the test stand-in for sign-in must never reach a Vercel deployment.
if (process.env.NEXT_PUBLIC_AUTH_MODE === "standin" && (process.env.VERCEL || process.env.VERCEL_ENV)) {
  throw new Error("NEXT_PUBLIC_AUTH_MODE=standin is for local tests only and must not be set on Vercel.");
}

const nextConfig: NextConfig = {
  poweredByHeader: false,
  // Inline the setting at build time ("" when unset), so the local-test sign-in code is removed from deployed
  // bundles instead of reading an empty browser-side process.env (stage 6: found in the deployed bundle).
  env: { NEXT_PUBLIC_AUTH_MODE: process.env.NEXT_PUBLIC_AUTH_MODE ?? "" },
  async headers() {
    return [{
      source: "/:path*",
      headers: securityHeaders({ apiUrl: process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000",
                                 supabaseUrl: process.env.NEXT_PUBLIC_SUPABASE_URL }),
    }];
  },
};

export default nextConfig;
