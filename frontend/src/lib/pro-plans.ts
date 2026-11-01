/**
 * Pro prices approved for the web and the stores (US tier).
 * Product ids match the ones the backend expects. Store products are
 * created in App Store Connect and Play Console, not in this repo.
 *
 * Keep the trial length and product ids in sync with
 * backend/app/core/native_billing_config.py.
 */

export const PRO_MONTHLY_PRICE_LABEL = "$6.99";
export const PRO_ANNUAL_PRICE_LABEL = "$49.99";
export const PRO_TRIAL_DAYS = 7;

export const PRO_MONTHLY_PRODUCT_ID =
  process.env.NEXT_PUBLIC_IAP_MONTHLY_PRODUCT_ID || "com.enchantedspoon.app.pro.monthly";
export const PRO_ANNUAL_PRODUCT_ID =
  process.env.NEXT_PUBLIC_IAP_ANNUAL_PRODUCT_ID || "com.enchantedspoon.app.pro.annual";

export const NATIVE_IAP_ENABLED = process.env.NEXT_PUBLIC_NATIVE_IAP_ENABLED === "true";
export const REVENUECAT_IOS_API_KEY = process.env.NEXT_PUBLIC_REVENUECAT_IOS_API_KEY ?? "";
export const REVENUECAT_ANDROID_API_KEY = process.env.NEXT_PUBLIC_REVENUECAT_ANDROID_API_KEY ?? "";
export const REVENUECAT_ENTITLEMENT_ID = "pro";

/** Web-only promotion code. There is no store offer code. */
export const FOUNDING_CODE = "FOUNDER30";
export const FOUNDING_PRICE_URL = "https://enchantedspoon.app/pricing#founding";

export type ProInterval = "month" | "year";

export function billingDate(from: Date, trialAvailable: boolean): Date {
  const next = new Date(from);
  if (trialAvailable) {
    next.setDate(next.getDate() + PRO_TRIAL_DAYS);
  }
  return next;
}

export function formatBillingDate(date: Date): string {
  return date.toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
  });
}
