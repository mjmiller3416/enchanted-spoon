// Sentry for the Next.js edge runtime (proxy.ts). See src/lib/sentry.ts.
import * as Sentry from "@sentry/nextjs";
import { sentryOptions } from "./src/lib/sentry";

Sentry.init(sentryOptions);
