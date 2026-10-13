import type { NextConfig } from "next";

// Safety: the test stand-in for sign-in must never reach a Vercel deployment.
if (process.env.NEXT_PUBLIC_AUTH_MODE === "standin" && (process.env.VERCEL || process.env.VERCEL_ENV)) {
  throw new Error("NEXT_PUBLIC_AUTH_MODE=standin is for local tests only and must not be set on Vercel.");
}

const nextConfig: NextConfig = {
  poweredByHeader: false,
  async headers() {
    return [{
      source: "/:path*",
      headers: [
        { key: "X-Content-Type-Options", value: "nosniff" },
        { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
        { key: "X-Frame-Options", value: "DENY" },
        { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
      ],
    }];
  },
};

export default nextConfig;
