import {
  NATIVE_IAP_ENABLED,
  PRO_ANNUAL_PRODUCT_ID,
  PRO_MONTHLY_PRODUCT_ID,
  REVENUECAT_ANDROID_API_KEY,
  REVENUECAT_IOS_API_KEY,
  type ProInterval,
} from "@/lib/pro-plans";
import { isNativeApp, nativePlatform } from "@/lib/native/platform";

export class NativePurchasesUnavailableError extends Error {
  constructor(message = "In-app purchases aren't turned on for this build yet.") {
    super(message);
    this.name = "NativePurchasesUnavailableError";
  }
}

export interface StorePriceLabels {
  monthly?: string;
  annual?: string;
}

function revenueCatApiKey(): string {
  return nativePlatform() === "android" ? REVENUECAT_ANDROID_API_KEY : REVENUECAT_IOS_API_KEY;
}

function assertPurchasesReady(): void {
  if (!isNativeApp()) {
    throw new NativePurchasesUnavailableError(
      "In-app purchases are only available in the iOS and Android apps.",
    );
  }
  if (!NATIVE_IAP_ENABLED || !revenueCatApiKey()) {
    throw new NativePurchasesUnavailableError();
  }
}

type PurchasesModule = typeof import("@revenuecat/purchases-capacitor");

async function purchasesModule(): Promise<PurchasesModule> {
  assertPurchasesReady();
  return import("@revenuecat/purchases-capacitor");
}

/**
 * Identify the store customer as our numeric account id. RevenueCat webhooks
 * then arrive with `app_user_id` equal to that id.
 */
export async function identifyStoreCustomer(userId: number): Promise<void> {
  if (!isNativeApp() || !NATIVE_IAP_ENABLED || !revenueCatApiKey()) return;
  const { Purchases } = await purchasesModule();
  const appUserID = String(userId);
  await Purchases.configure({
    apiKey: revenueCatApiKey(),
    appUserID,
  });
  await Purchases.logIn({ appUserID });
}

function productMatches(identifier: string, productId: string): boolean {
  // Play Billing may report `productId:basePlanId`.
  return identifier === productId || identifier.startsWith(`${productId}:`);
}

export async function loadStorePrices(): Promise<StorePriceLabels> {
  if (!isNativeApp() || !NATIVE_IAP_ENABLED || !revenueCatApiKey()) return {};
  const { Purchases } = await purchasesModule();
  const offerings = await Purchases.getOfferings();
  const packages = offerings.current?.availablePackages ?? [];
  const labels: StorePriceLabels = {};
  for (const pack of packages) {
    const productId = pack.product.identifier;
    const price = pack.product.priceString;
    if (productMatches(productId, PRO_MONTHLY_PRODUCT_ID)) labels.monthly = price;
    if (productMatches(productId, PRO_ANNUAL_PRODUCT_ID)) labels.annual = price;
  }
  return labels;
}

/**
 * App Store storefront country. Null when StoreKit isn't configured.
 * A missing storefront must not show the web founding link.
 */
export async function loadAppleStorefrontCountry(): Promise<string | null> {
  if (nativePlatform() !== "ios" || !NATIVE_IAP_ENABLED || !REVENUECAT_IOS_API_KEY) {
    return null;
  }
  try {
    const { Purchases } = await purchasesModule();
    const storefront = await Purchases.getStorefront();
    return storefront.countryCode || null;
  } catch {
    return null;
  }
}

export async function purchasePlan(interval: ProInterval): Promise<void> {
  const { Purchases } = await purchasesModule();
  const offerings = await Purchases.getOfferings();
  const packages = offerings.current?.availablePackages ?? [];
  const productId = interval === "year" ? PRO_ANNUAL_PRODUCT_ID : PRO_MONTHLY_PRODUCT_ID;
  const match = packages.find((pack) => productMatches(pack.product.identifier, productId));
  if (!match) {
    throw new NativePurchasesUnavailableError("That plan isn't available from the store yet.");
  }
  await Purchases.purchasePackage({ aPackage: match });
}

export async function restorePurchases(): Promise<void> {
  const { Purchases } = await purchasesModule();
  await Purchases.restorePurchases();
}
