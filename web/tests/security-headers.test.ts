import { describe, expect, test } from "vitest";
import { contentSecurityPolicy, securityHeaders } from "@/config/headers";

const API = "https://roundup-demo-api-pr.vercel.app", SB = "https://abc123.supabase.co";
const directive = (csp: string, name: string) => csp.split(";").map((d) => d.trim()).find((d) => d.startsWith(name + " ")) ?? "";

describe("security headers (stage 6: deployed preview had no Content-Security-Policy)", () => {
  const csp = contentSecurityPolicy({ apiUrl: API, supabaseUrl: SB });
  test("locks down framing, plugins, base URI and form targets", () => {
    expect(directive(csp, "frame-ancestors")).toBe("frame-ancestors 'none'");
    expect(directive(csp, "object-src")).toBe("object-src 'none'");
    expect(directive(csp, "base-uri")).toBe("base-uri 'self'");
    expect(directive(csp, "form-action")).toBe("form-action 'self'");
    expect(directive(csp, "default-src")).toBe("default-src 'self'");
  });
  test("the browser may talk only to this site, the API and Supabase", () => {
    expect(directive(csp, "connect-src")).toBe(`connect-src 'self' ${API} ${SB}`);
    expect(csp).not.toContain("*");
    expect(directive(csp, "connect-src")).not.toContain("data:");
  });
  test("no remote scripts, no eval; inline allowed only where Next.js and React need it", () => {
    expect(directive(csp, "script-src")).toBe("script-src 'self' 'unsafe-inline'");
    expect(csp).not.toContain("unsafe-eval");
    expect(directive(csp, "img-src")).toBe("img-src 'self' data:");
  });
  test("unset addresses add nothing (no empty or wildcard entries)", () => {
    expect(directive(contentSecurityPolicy({}), "connect-src")).toBe("connect-src 'self'");
  });
  test("malformed addresses are reduced to their origin, so a typo cannot widen the policy", () => {
    const c = contentSecurityPolicy({ apiUrl: `${API}/v1/path?x=1; script-src *`, supabaseUrl: "not a url" });
    expect(directive(c, "connect-src")).toBe(`connect-src 'self' ${API}`);
    expect(c).not.toContain("script-src *");
  });
  test("the header list carries the policy and the earlier headers", () => {
    const h = Object.fromEntries(securityHeaders({ apiUrl: API, supabaseUrl: SB }).map((x) => [x.key, x.value]));
    expect(h["Content-Security-Policy"]).toBe(csp);
    expect(h["X-Content-Type-Options"]).toBe("nosniff");
    expect(h["X-Frame-Options"]).toBe("DENY");
    expect(h["Referrer-Policy"]).toBe("strict-origin-when-cross-origin");
    expect(h["Permissions-Policy"]).toContain("camera=()");
  });
});
