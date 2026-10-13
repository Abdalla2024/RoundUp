// Security response headers for the web app (used by next.config.ts, tested in tests/security-headers.test.ts).
// Next.js and React emit small inline scripts and use inline styles, so script-src and style-src allow
// 'unsafe-inline'; everything else is closed (no remote scripts, no eval, no framing, only our API and Supabase).

const origin = (url?: string): string | null => {
  if (!url) return null;
  try { const u = new URL(url); return u.protocol === "https:" || u.protocol === "http:" ? u.origin : null; } catch { return null; }
};

export interface Addresses { apiUrl?: string; supabaseUrl?: string }

export function contentSecurityPolicy({ apiUrl, supabaseUrl }: Addresses): string {
  const connect = ["'self'", origin(apiUrl), origin(supabaseUrl)].filter((x): x is string => Boolean(x));
  return [
    "default-src 'self'",
    "script-src 'self' 'unsafe-inline'",
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data:",
    "font-src 'self'",
    `connect-src ${[...new Set(connect)].join(" ")}`,
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "object-src 'none'",
  ].join("; ");
}

export function securityHeaders(a: Addresses): { key: string; value: string }[] {
  return [
    { key: "Content-Security-Policy", value: contentSecurityPolicy(a) },
    { key: "X-Content-Type-Options", value: "nosniff" },
    { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
    { key: "X-Frame-Options", value: "DENY" },
    { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
  ];
}
