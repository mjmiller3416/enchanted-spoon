import type { NativePlatform } from "./platform";

/**
 * Where the web-only FOUNDER30 price may be mentioned inside the app.
 *
 * Apple Guideline 3.1.1(a), as published for the United States storefront:
 * buttons and external links to other purchase methods do not need a
 * StoreKit External Purchase Link entitlement on that storefront. The same
 * guideline still prohibits those links on every other storefront unless
 * the app holds the regional entitlement. This build does not.
 *
 * Google Play's External Content Links program (US) requires enrollment,
 * a destination registered in Play Console, and the Play Billing external
 * link API (information screen, then `launchExternalLink`). This app is
 * not enrolled, so Android never shows the link. Do not flip that by
 * revealing the offer in the WebView.
 */
export function appleStorefrontAllowsWebFoundingLink(
  countryCode: string | null | undefined,
): boolean {
  const code = (countryCode ?? "").trim().toUpperCase();
  return code === "US" || code === "USA";
}

export function mayMentionWebFoundingOffer(
  platform: NativePlatform,
  appleStorefrontCountry: string | null,
): boolean {
  if (platform === "web") return true;
  if (platform === "ios") return appleStorefrontAllowsWebFoundingLink(appleStorefrontCountry);
  return false;
}
