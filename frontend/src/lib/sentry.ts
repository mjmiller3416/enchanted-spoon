/**
 * Sentry options shared by the browser, server and edge runtimes.
 *
 * Nothing is sent without NEXT_PUBLIC_SENTRY_DSN. Events carry only the
 * internal user id (set by ErrorReportingUser) — no cookies, headers, bodies
 * or automatically collected user info (IP, email).
 */
export const sentryOptions = {
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  environment: process.env.NEXT_PUBLIC_SENTRY_ENVIRONMENT ?? process.env.NODE_ENV,
  dataCollection: {
    userInfo: false,
    cookies: false,
    httpHeaders: false,
    httpBodies: [],
  },
  // Errors only; raise to sample performance traces
  tracesSampleRate: 0,
};
