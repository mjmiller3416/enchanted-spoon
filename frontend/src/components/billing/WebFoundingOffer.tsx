import { FOUNDING_CODE, FOUNDING_PRICE_URL } from "@/lib/pro-plans";

/**
 * Web-only founding price. Hidden in native builds by CSS until the
 * platform is allowed to link out. See `lib/native/founding-offer.ts`.
 * The anchor carries `data-external-purchase` so the native shell opens
 * it in the system browser instead of Stripe Checkout inside the WebView.
 */
export function WebFoundingOffer() {
  return (
    <p id="founding" className="web-founding-offer text-sm text-muted-foreground">
      Founding offer: enter code{" "}
      <span className="font-medium text-foreground">{FOUNDING_CODE}</span> at checkout on the
      web.{" "}
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
