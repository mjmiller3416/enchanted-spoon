"use client";

import { useClerk } from "@clerk/nextjs";
import { useEffect, useState } from "react";
import { environmentUrl, oauthStrategyEnabled, readBrowserClerk } from "@/lib/native/social-sign-in";

function firstKnown(values: Array<boolean | null>): boolean | null {
  for (const value of values) {
    if (value !== null) return value;
  }
  return null;
}

/**
 * True only when this Clerk instance has Sign in with Apple enabled.
 * The button stays hidden until then, including while the environment
 * request is still in flight.
 */
export function useAppleSignInOffered(): boolean {
  const clerk = useClerk();
  const known = clerk.loaded
    ? firstKnown([
        oauthStrategyEnabled(clerk, "oauth_apple"),
        oauthStrategyEnabled(readBrowserClerk(), "oauth_apple"),
      ])
    : null;
  const [fromApi, setFromApi] = useState<boolean | null>(null);
  const frontendApi = clerk.frontendApi;

  useEffect(() => {
    if (known !== null) return;
    const url = environmentUrl(frontendApi);
    if (!url) return;

    const controller = new AbortController();
    void fetch(url, { signal: controller.signal })
      .then((response) => (response.ok ? response.json() : null))
      .then((data: unknown) => {
        setFromApi(oauthStrategyEnabled(data, "oauth_apple") === true);
      })
      .catch(() => {
        if (!controller.signal.aborted) setFromApi(false);
      });

    return () => controller.abort();
  }, [known, frontendApi]);

  if (known !== null) return known;
  return fromApi === true;
}
