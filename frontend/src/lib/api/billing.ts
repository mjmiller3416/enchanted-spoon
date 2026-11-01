import type {
  CheckoutSessionResponse,
  CurrentUserUsage,
  FounderOffer,
  PortalSessionResponse,
  StoreSyncResponse,
} from "@/types/billing";
import { fetchApi } from "./base";

export const billingApi = {
  /** Create a Stripe Checkout session. plan selects the monthly or annual price. */
  createCheckoutSession: (
    plan: "monthly" | "annual" = "monthly",
    promotionCode?: string,
    token?: string | null,
  ): Promise<CheckoutSessionResponse> =>
    fetchApi<CheckoutSessionResponse>(
      "/api/billing/checkout-session",
      {
        method: "POST",
        body: JSON.stringify({
          plan,
          ...(promotionCode ? { promotion_code: promotionCode } : {}),
        }),
      },
      token,
    ),

  /**
   * Ask the server to read this account's store entitlement from RevenueCat.
   * The client cannot grant itself Pro.
   */
  syncStoreEntitlement: (token?: string | null): Promise<StoreSyncResponse> =>
    fetchApi<StoreSyncResponse>("/api/billing/store/sync", { method: "POST" }, token),

  founderOffer: (token?: string | null): Promise<FounderOffer> =>
    fetchApi<FounderOffer>("/api/billing/founder-offer", undefined, token),

  dismissSunsetNotice: (token?: string | null) =>
    fetchApi("/api/users/me/sunset-notice", { method: "POST" }, token),

  /** Create a Stripe billing-portal session; redirect to the returned URL. */
  createPortalSession: (token?: string | null): Promise<PortalSessionResponse> =>
    fetchApi<PortalSessionResponse>(
      "/api/billing/portal-session",
      { method: "POST" },
      token,
    ),

  /** Current month's AI usage counters and tier caps for the signed-in user. */
  getMyUsage: (token?: string | null): Promise<CurrentUserUsage> =>
    fetchApi<CurrentUserUsage>("/api/users/me/usage", undefined, token),
};
