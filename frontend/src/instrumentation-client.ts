// Sentry in the browser. Events go through the /monitoring tunnel
// (next.config.ts) so ad blockers don't drop them. See src/lib/sentry.ts.
import * as Sentry from "@sentry/nextjs";
import { sentryOptions } from "@/lib/sentry";

Sentry.init(sentryOptions);

export const onRouterTransitionStart = Sentry.captureRouterTransitionStart;
