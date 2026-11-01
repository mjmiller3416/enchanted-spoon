"use client";

import { useEffect, useState } from "react";
import { FOUNDING_CODE, FOUNDING_PRICE_URL } from "@/lib/pro-plans";
import { isFoundingOfferOpen } from "@/lib/plan-sunset";

/**
 * Web-only founding price. Hidden after the shared plan sunset
 * (March 31, 2027, 11:59 PM America/New_York by default), and hidden in
 * native builds by CSS until the platform is allowed to link out.
 * The anchor carries `data-external-purchase` so the native shell opens
 * it in the system browser instead of Stripe Checkout inside the WebView.
 */
export function WebFoundingOffer() {
  const [open, setOpen] = useState(true);

  useEffect(() => {
    setOpen(isFoundingOfferOpen(new Date()));
  }, []);

  if (!open) return null;

  return (
    <p id="founding" className="web-founding-offer text-sm text-muted-foreground">
      Founding offer: enter code{" "}
      <span className="font-medium text-foreground">{FOUNDING_CODE}</span> at checkout on the
      web. It ends at the same time the grandfathered free plan does.{" "}
      <a
        href={FOUNDING_PRICE_URL}
        data-external-purchase="true"
        className="native-founding-link font-medium text-primary underline-offset-4 hover:underline"
      >
        View founding price
      </a>
    </p>
  );
}
