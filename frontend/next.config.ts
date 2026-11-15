import type { NextConfig } from "next";
import { withSentryConfig } from "@sentry/nextjs/config";

// Baseline security headers applied to every response. A Content-Security-Policy
// is intentionally omitted here — it needs a careful allowlist for Clerk,
// Cloudinary, and the API origin and is tracked as a separate hardening task.
const securityHeaders = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "SAMEORIGIN" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "X-DNS-Prefetch-Control", value: "on" },
  {
    key: "Strict-Transport-Security",
    value: "max-age=31536000; includeSubDomains",
  },
  {
    key: "Permissions-Policy",
    value: "camera=(), microphone=(), geolocation=(), interest-cohort=()",
  },
];

// The ChatGPT connector (MCP server + OAuth) lives in the backend, but its URL
// is this site's: https://<site>/api/mcp. These paths are proxied to the
// backend so the one URL people paste, the OAuth issuer and the discovery
// documents all share this origin. Read at build time, like NEXT_PUBLIC_*.
const backendUrl = (process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001").replace(/\/+$/, "");

const connectorRewrites = [
  "/api/mcp",
  "/api/oauth/:path*",
  "/.well-known/oauth-protected-resource",
  "/.well-known/oauth-protected-resource/:path*",
  "/.well-known/oauth-authorization-server",
].map((source) => ({ source, destination: `${backendUrl}${source}` }));

const nextConfig: NextConfig = {
  // Enable standalone output for Docker deployments
  output: "standalone",
  outputFileTracingRoot: process.cwd(),

  async rewrites() {
    return connectorRewrites;
  },

  async headers() {
    return [
      {
        source: "/:path*",
        headers: securityHeaders,
      },
    ];
  },
};

// Source maps upload only when SENTRY_AUTH_TOKEN is present at build time;
// without SENTRY_DSN / NEXT_PUBLIC_SENTRY_DSN nothing is reported at all.
export default withSentryConfig(nextConfig, {
  org: process.env.SENTRY_ORG,
  project: process.env.SENTRY_PROJECT,
  authToken: process.env.SENTRY_AUTH_TOKEN,
  // Railway provides the deployed commit; ties each error to its build
  release: { name: process.env.RAILWAY_GIT_COMMIT_SHA },
  // Excluded from Clerk in proxy.ts so signed-out pages can report too
  tunnelRoute: "/monitoring",
  widenClientFileUpload: true,
  telemetry: false,
  silent: !process.env.CI,
});
