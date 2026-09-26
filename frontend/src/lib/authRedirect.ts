const DEFAULT_AFTER_AUTH = "/dashboard";

/**
 * Where to send the user after signing in or up. Honors the `redirect_url`
 * Clerk's middleware adds when it bounces a deep link to /sign-in, but only
 * for same-origin paths so the param can't be used as an open redirect.
 */
export function getPostAuthRedirect(): string {
  if (typeof window === "undefined") return DEFAULT_AFTER_AUTH;
  const raw = new URLSearchParams(window.location.search).get("redirect_url");
  if (!raw) return DEFAULT_AFTER_AUTH;
  try {
    const url = new URL(raw, window.location.origin);
    if (url.origin !== window.location.origin) return DEFAULT_AFTER_AUTH;
    const path = `${url.pathname}${url.search}${url.hash}`;
    // Never bounce back into the auth pages themselves
    if (/^\/(sign-in|sign-up|sso-callback)(\/|$)/.test(url.pathname)) return DEFAULT_AFTER_AUTH;
    return path || DEFAULT_AFTER_AUTH;
  } catch {
    return DEFAULT_AFTER_AUTH;
  }
}
