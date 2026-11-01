/** Web Pro prices. Stripe Tax is exclusive, so the displayed price is before tax. */

export const PRO_MONTHLY_PRICE = "$6.99";
export const PRO_ANNUAL_PRICE = "$49.99";
export const TAX_SUFFIX = "plus applicable tax";
export const MONTHLY_PRICE_LABEL = `${PRO_MONTHLY_PRICE}/mo ${TAX_SUFFIX}`;
export const ANNUAL_PRICE_LABEL = `${PRO_ANNUAL_PRICE}/yr ${TAX_SUFFIX}`;

export type CheckoutPlan = "monthly" | "annual";
