/**
 * Sentry options shared by the browser, server and edge runtimes.
 *
 * Nothing is sent without NEXT_PUBLIC_SENTRY_DSN. Events carry only the
 * internal user id (set by ErrorReportingUser) — no cookies, headers, bodies
 * or automatically collected user info (IP, email).
 */
import type { ErrorEvent as SentryErrorEvent, EventHint } from "@sentry/nextjs";

import { describeResourceErrorRejection } from "@/lib/sentry-resource-error";

function beforeSend(event: SentryErrorEvent, hint: EventHint): SentryErrorEvent | null {
  const described = describeResourceErrorRejection(hint.originalException);
  if (!described) return event;
  if (described.ignore) return null;

  event.message = described.message;
  const values = event.exception?.values;
  if (values && values.length > 0) {
    for (const entry of values) {
      entry.value = described.message;
      if (!entry.type || entry.type === "Event" || entry.type === "UnhandledRejection") {
        entry.type = "ResourceLoadError";
      }
    }
  } else {
    event.exception = {
      values: [{ type: "ResourceLoadError", value: described.message }],
    };
  }
  event.extra = {
    ...event.extra,
    tagName: described.extras.tagName,
    src: described.extras.src,
    href: described.extras.href,
  };
  return event;
}

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
  // Resource error events reject with a DOM Event and no stack. Name the
  // element that failed, and drop browser-extension URLs. Other events pass
  // through unchanged.
  beforeSend,
};
