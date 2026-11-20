/**
 * The Clerk publishable key embeds the Frontend API host (base64), the same
 * way the backend derives its JWKS URL. The native sign-in client calls that
 * host directly and never the cookie-based clerk-js instance.
 */

export function clerkFrontendHost(publishableKey: string | null | undefined): string | null {
  if (!publishableKey) return null;
  const key = publishableKey.trim();
  if (!key.startsWith("pk_test_") && !key.startsWith("pk_live_")) return null;

  let encoded = key.slice("pk_test_".length);
  if (encoded.endsWith("$")) encoded = encoded.slice(0, -1);
  encoded = encoded.replace(/-/g, "+").replace(/_/g, "/");
  const remainder = encoded.length % 4;
  if (remainder) encoded += "=".repeat(4 - remainder);

  let decoded: string;
  try {
    decoded = atob(encoded);
  } catch {
    return null;
  }

  const host = decoded.replace(/\$+$/, "");
  if (!/^[a-z0-9.-]+$/i.test(host)) return null;
  if (host.startsWith(".") || host.endsWith(".") || host.includes("..")) return null;
  return host;
}
